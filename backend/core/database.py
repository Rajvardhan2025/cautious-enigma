import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False

    async def connect(self):
        """Connect to MongoDB"""
        if self.connected:
            return

        try:
            mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
            db_name = os.getenv("MONGODB_DB_NAME", "voice_agent")

            self.client = AsyncIOMotorClient(mongodb_uri)
            self.db = self.client[db_name]

            # Test connection
            await self.client.admin.command("ping")
            self.connected = True

            # Create indexes
            await self._create_indexes()

            logger.info(f"[Database] Connected to {db_name}")

        except Exception as e:
            logger.error(f"[Database] Connection failed: {e}")
            raise

    async def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # User indexes
            await self.db.users.create_index("phone", unique=True)

            # Appointment indexes
            await self.db.appointments.create_index([("user_id", 1), ("datetime", 1)])
            await self.db.appointments.create_index([("date", 1), ("time", 1)])
            await self.db.appointments.create_index("status")

            # Conversation summary indexes
            await self.db.conversation_summaries.create_index(
                "conversation_id", unique=True
            )
            await self.db.conversation_summaries.create_index(
                [("user_id", 1), ("conversation_date", -1)]
            )

            # Conversation messages indexes
            await self.db.conversation_messages.create_index(
                "conversation_id", unique=True
            )
            await self.db.conversation_messages.create_index(
                [("user_id", 1), ("timestamp", -1)]
            )

        except Exception as e:
            logger.error(f"[Database] Index creation error: {e}")

    async def ensure_connected(self):
        """Ensure database connection is active"""
        if not self.connected:
            await self.connect()

    # User operations
    async def create_user(self, user_data: Dict) -> ObjectId:
        """Create a new user"""
        await self.ensure_connected()

        try:
            result = await self.db.users.insert_one(user_data)
            return result.inserted_id

        except Exception as e:
            logger.error(f"[Database] Create user error: {e}")
            raise

    async def get_user_by_phone(self, phone: str) -> Optional[Dict]:
        """Get user by phone number"""
        await self.ensure_connected()

        try:
            user = await self.db.users.find_one({"phone": phone})
            return user

        except Exception as e:
            logger.error(f"[Database] Get user by phone error: {e}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        await self.ensure_connected()

        try:
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            return user

        except Exception as e:
            logger.error(f"[Database] Get user by ID error: {e}")
            return None

    async def update_user(self, user_id: str, updates: Dict) -> bool:
        """Update user information"""
        await self.ensure_connected()

        try:
            result = await self.db.users.update_one(
                {"_id": ObjectId(user_id)}, {"$set": updates}
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"[Database] Update user error: {e}")
            return False

    # Appointment operations
    async def create_appointment(self, appointment_data: Dict) -> ObjectId:
        """Create a new appointment"""
        await self.ensure_connected()

        try:
            result = await self.db.appointments.insert_one(appointment_data)
            return result.inserted_id

        except Exception as e:
            logger.error(f"[Database] Create appointment error: {e}")
            raise

    async def get_appointment_by_id(
        self, appointment_id: str, user_id: str
    ) -> Optional[Dict]:
        """Get appointment by ID for a specific user"""
        await self.ensure_connected()

        try:
            appointment = await self.db.appointments.find_one(
                {"_id": ObjectId(appointment_id), "user_id": user_id}
            )
            return appointment

        except Exception as e:
            logger.error(f"[Database] Get appointment by ID error: {e}")
            return None

    async def get_appointment_by_datetime(
        self, user_id: str, date: str, time: str
    ) -> Optional[Dict]:
        """Get appointment by date and time for a specific user"""
        await self.ensure_connected()

        try:
            appointment = await self.db.appointments.find_one(
                {
                    "user_id": user_id,
                    "date": date,
                    "time": time,
                    "status": {"$ne": "cancelled"},
                }
            )
            return appointment

        except Exception as e:
            logger.error(f"[Database] Get appointment by datetime error: {e}")
            return None

    async def get_user_appointments(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get all appointments for a user"""
        await self.ensure_connected()

        try:
            cursor = (
                self.db.appointments.find({"user_id": user_id})
                .sort("datetime", -1)
                .limit(limit)
            )

            appointments = await cursor.to_list(length=limit)
            return appointments

        except Exception as e:
            logger.error(f"[Database] Get user appointments error: {e}")
            return []

    async def get_booked_slots(self, date: str) -> List[str]:
        """Get all booked slots for a specific date"""
        await self.ensure_connected()

        try:
            cursor = self.db.appointments.find(
                {"date": date, "status": {"$ne": "cancelled"}}
            )

            appointments = await cursor.to_list(length=None)
            booked_slots = [f"{apt['date']} {apt['time']}" for apt in appointments]
            return booked_slots

        except Exception as e:
            logger.error(f"[Database] Get booked slots error: {e}")
            return []

    async def update_appointment(self, appointment_id: ObjectId, updates: Dict) -> bool:
        """Update appointment details"""
        await self.ensure_connected()

        try:
            updates["updated_at"] = datetime.utcnow()
            result = await self.db.appointments.update_one(
                {"_id": appointment_id}, {"$set": updates}
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"[Database] Update appointment error: {e}")
            return False

    async def update_appointment_status(
        self, appointment_id: ObjectId, status: str
    ) -> bool:
        """Update appointment status"""
        await self.ensure_connected()

        try:
            result = await self.db.appointments.update_one(
                {"_id": appointment_id},
                {"$set": {"status": status, "updated_at": datetime.utcnow()}},
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"[Database] Update appointment status error: {e}")
            return False

    # Conversation summary operations
    async def save_conversation_summary(self, summary_data: Dict) -> ObjectId:
        """Save conversation summary"""
        await self.ensure_connected()

        try:
            result = await self.db.conversation_summaries.insert_one(summary_data)
            return result.inserted_id

        except Exception as e:
            logger.error(f"[Database] Save conversation summary error: {e}")
            raise

    async def save_conversation_messages(self, messages_data: Dict) -> ObjectId:
        """Save all conversation messages for a session"""
        await self.ensure_connected()

        try:
            result = await self.db.conversation_messages.insert_one(messages_data)
            return result.inserted_id

        except Exception as e:
            logger.error(f"[Database] Save conversation messages error: {e}")
            raise

    async def get_conversation_messages(self, conversation_id: str) -> Optional[Dict]:
        """Get all messages for a specific conversation"""
        await self.ensure_connected()

        try:
            messages = await self.db.conversation_messages.find_one(
                {"conversation_id": conversation_id}
            )
            return messages

        except Exception as e:
            logger.error(f"[Database] Get conversation messages error: {e}")
            return None

    async def get_user_conversation_summaries(
        self, user_id: str, limit: int = 10
    ) -> List[Dict]:
        """Get conversation summaries for a user"""
        await self.ensure_connected()

        try:
            cursor = (
                self.db.conversation_summaries.find({"user_id": user_id})
                .sort("conversation_date", -1)
                .limit(limit)
            )

            summaries = await cursor.to_list(length=limit)
            return summaries

        except Exception as e:
            logger.error(f"[Database] Get conversation summaries error: {e}")
            return []

    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("[Database] Connection closed")
