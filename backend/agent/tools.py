import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

import dateparser

from livekit.agents import (
    Agent,
    RunContext,
    function_tool,
    get_job_context,
)

from core.database import DatabaseManager
from core.models import Appointment

logger = logging.getLogger("agent.tools")

ALLOWED_TIMES = ["12:00", "15:00", "17:00", "18:00", "19:00"]




@dataclass
class ConversationContext:
    user_id: Optional[str] = None
    user_phone: Optional[str] = None
    user_name: Optional[str] = None
    conversation_history: List[Dict] = None
    pending_appointment: Optional[Dict] = None
    last_user_message: Optional[str] = None
    last_agent_message: Optional[str] = None
    last_tool_call: Optional[Dict] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []


class VoiceAppointmentAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a friendly appointment booking assistant. Keep responses SHORT and conversational.

CRITICAL RULES:
- Speak naturally like a human, not a robot
- Keep responses under 2 sentences when possible
- Never read out technical details, IDs, or system messages
- Only speak the essential information the user needs to hear
- Ask ONE question at a time
- Do NOT show internal reasoning, planning, or tool-calling details
- Do NOT mention rules, policies, or that you're waiting (e.g., "we should wait for the user")
- Do NOT repeat yourself or ask the same thing multiple times
- If a detail is missing, ask a single, direct question and stop
- Only call tools after the user has clearly provided the required info
- When confirming, ask once and wait for a clear yes/no

Your job:
1. Get phone number to identify user
2. Help book, view, modify, or cancel appointments
3. Confirm details clearly and briefly

When booking:
- Appointments are ONLY available for tomorrow
- Available times are: 12 PM, 3 PM, 5 PM, 6 PM, 7 PM
- Ask for the time only (one at a time)
- Confirm briefly: "Got it, booked for tomorrow at [time]"
- Don't read appointment IDs or technical details
- If the user asks for another day, tell them only tomorrow is available
- If the user asks for another time, offer the allowed times again

When the user wants to end the call (e.g., "cut the call", "hang up", "bye"), call the end_conversation tool.

Be warm, brief, and helpful.""",
        )
        logger.debug("🤖 VoiceAppointmentAgent initialized")
        self.db = DatabaseManager()
        self.context = ConversationContext()
        logger.debug("✅ Database manager and conversation context ready")

    def _normalize_date(self, date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None

        parsed = dateparser.parse(
            date_str,
            settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
        )
        if not parsed:
            return None
        return parsed.date().isoformat()

    def _normalize_time(self, time_str: Optional[str]) -> Optional[str]:
        if not time_str:
            return None

        parsed = dateparser.parse(
            time_str,
            settings={"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
        )
        if not parsed:
            return None
        return parsed.strftime("%H:%M")

    def _tomorrow_date(self) -> str:
        return (datetime.now().date() + timedelta(days=1)).isoformat()

    def _allowed_slots_for_date(self, date: Optional[str] = None) -> List[Dict[str, str]]:
        tomorrow = self._tomorrow_date()
        if date and date != tomorrow:
            return []
        return [{"date": tomorrow, "time": t} for t in ALLOWED_TIMES]

    def _is_allowed_slot(self, date: str, time: str) -> bool:
        tomorrow = self._tomorrow_date()
        return date == tomorrow and time in ALLOWED_TIMES

    def _format_slots(self, slots: List[Dict[str, str]]) -> str:
        if not slots:
            return ""
        return ", ".join([self._format_time_ampm(slot["time"]) for slot in slots])

    def _format_time_ampm(self, time_24h: str) -> str:
        try:
            return datetime.strptime(time_24h, "%H:%M").strftime("%-I %p")
        except Exception:
            return time_24h

    def _get_room_from_context(self, context: RunContext):
        """Best-effort room access for sending data events."""
        try:
            session = getattr(context, "session", None)
            if session and getattr(session, "room", None):
                return session.room
        except Exception:
            pass

        try:
            return get_job_context().room
        except Exception:
            return None

    async def _publish_data_event(self, context: RunContext, payload: Dict):
        """Publish a JSON event to the LiveKit data channel."""
        try:
            import json
            room = self._get_room_from_context(context)

            if not room:
                logger.warning("⚠️  No room context available to send data event")
                return

            await room.local_participant.publish_data(
                json.dumps(payload, default=str).encode("utf-8"),
                reliable=True,
            )
        except Exception as e:
            logger.error(f"❌ Error sending data event: {e}", exc_info=True)

    async def _send_tool_call_event(self, context: RunContext, tool_name: str, parameters: Dict, result: str):
        """Send tool call event to frontend for display"""
        event_data = {
            "type": "tool_call",
            "tool_name": tool_name,
            "parameters": parameters,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success",
        }

        self.context.last_tool_call = {
            "tool_name": tool_name,
            "parameters": parameters,
            "result": result,
            "timestamp": event_data["timestamp"],
        }

        await self._publish_data_event(context, event_data)
        logger.info(f"tool: {tool_name} | params: {parameters}")
        logger.debug(f"📤 Sent tool call event to frontend: {tool_name}")

    async def _say_response(self, context: RunContext, text: str) -> None:
        """Speak the tool response verbatim to avoid LLM paraphrasing."""
        try:
            session = getattr(context, "session", None)
            if session:
                await session.say(text, allow_interruptions=True)
                self.context.last_agent_message = text
        except Exception as e:
            logger.error(f"❌ Error speaking tool response: {e}", exc_info=True)

    @function_tool
    async def identify_user(self, context: RunContext, phone_number: str) -> str:
        """Identify a user by their phone number.
        
        Args:
            phone_number: The user's phone number for identification
        """
        logger.info(f"🔍 identify_user: {phone_number}")
        
        try:
            # Clean phone number
            clean_phone = ''.join(filter(str.isdigit, phone_number))
            
            user = await self.db.get_user_by_phone(clean_phone)
            if user:
                self.context.user_id = str(user['_id'])
                self.context.user_phone = clean_phone
                self.context.user_name = user.get('name', 'User')
                
                logger.info(f"✅ User found: {self.context.user_name}")
                response = (
                    f"Welcome back! What time tomorrow works for you—"
                    f"{', '.join(['12 PM','3 PM','5 PM','6 PM','7 PM'])}?"
                )
            else:
                # Create new user
                user_data = {
                    'phone': clean_phone,
                    'name': 'User',
                    'created_at': datetime.utcnow()
                }
                user_id = await self.db.create_user(user_data)
                self.context.user_id = str(user_id)
                self.context.user_phone = clean_phone
                self.context.user_name = 'User'
                
                logger.info(f"✅ New user created")
                response = (
                    "Thanks! What time tomorrow works for you—"
                    "12 PM, 3 PM, 5 PM, 6 PM, or 7 PM?"
                )
            
            # Send tool call event to frontend
            await self._send_tool_call_event(context, "identify_user", {"phone_number": phone_number}, response)
            await self._say_response(context, response)
            return None
                
        except Exception as e:
            logger.error(f"❌ Error identifying user: {e}", exc_info=True)
            response = "Sorry, I couldn't find that number. Can you try again?"
            await self._say_response(context, response)
            return None

    @function_tool
    async def fetch_slots(self, context: RunContext, date: str = None) -> str:
        """Fetch available appointment slots for a given date.
        
        Args:
            date: Date to check slots for (YYYY-MM-DD format). If not provided, shows next 7 days.
        """
        logger.info(f"📅 fetch_slots: {date or 'allowed slots'}")
        
        try:
            normalized_date = self._normalize_date(date) if date else None
            tomorrow = self._tomorrow_date()
            allowed_slots = self._allowed_slots_for_date(tomorrow)

            response = (
                f"Tomorrow I have {self._format_slots(allowed_slots)}. Which time works for you?"
            )
            
            await self._send_tool_call_event(context, "fetch_slots", {"date": normalized_date or date}, response)
            await self._say_response(context, response)
            return None
                    
        except Exception as e:
            logger.error(f"❌ Error fetching slots: {e}", exc_info=True)
            response = "Can't check slots right now. Try again?"
            await self._say_response(context, response)
            return None

    @function_tool
    async def book_appointment(self, context: RunContext, date: str, time: str, purpose: str = "General consultation") -> str:
        """Book an appointment for the identified user.
        
        Args:
            date: Appointment date (YYYY-MM-DD format)
            time: Appointment time (HH:MM format)
            purpose: Purpose or reason for the appointment
        """
        logger.info(f"📝 book_appointment: {date} {time}")
        
        if not self.context.user_id:
            logger.warning("⚠️  Cannot book appointment: User not identified")
            response = "I need your phone number first."
            await self._say_response(context, response)
            return None
        
        try:
            normalized_date = self._tomorrow_date()
            normalized_time = self._normalize_time(time)
            tomorrow = self._tomorrow_date()

            if not normalized_date or not normalized_time:
                response = (
                    "I can only book for tomorrow. "
                    f"Which time works for you: {self._format_slots(self._allowed_slots_for_date(tomorrow))}?"
                )
                await self._send_tool_call_event(
                    context,
                    "book_appointment",
                    {"date": date, "time": time, "purpose": purpose},
                    response,
                )
                await self._say_response(context, response)
                return None

            if not self._is_allowed_slot(normalized_date, normalized_time):
                response = (
                    f"Tomorrow I can do {self._format_slots(self._allowed_slots_for_date(tomorrow))}. "
                    "Which time should I book?"
                )

                await self._send_tool_call_event(
                    context,
                    "book_appointment",
                    {"date": normalized_date, "time": normalized_time, "purpose": purpose},
                    response,
                )
                await self._say_response(context, response)
                return None

            # Check if slot is already booked
            datetime_str = f"{normalized_date} {normalized_time}"
            booked_slots = await self.db.get_booked_slots(normalized_date)

            if datetime_str in booked_slots:
                logger.warning(f"⚠️  Slot {datetime_str} is already booked")
                response = f"Sorry, {normalized_time} on {normalized_date} is taken. Want a different slot?"
                await self._send_tool_call_event(
                    context,
                    "book_appointment",
                    {"date": normalized_date, "time": normalized_time, "purpose": purpose},
                    response,
                )
                await self._say_response(context, response)
                return None
            
            # Create appointment
            appointment_data = {
                'user_id': self.context.user_id,
                'date': normalized_date,
                'time': normalized_time,
                'datetime': datetime.strptime(f"{normalized_date} {normalized_time}", "%Y-%m-%d %H:%M"),
                'purpose': purpose,
                'status': 'confirmed',
                'created_at': datetime.utcnow()
            }
            
            appointment_id = await self.db.create_appointment(appointment_data)
            
            # Store in context for summary
            self.context.pending_appointment = {
                'id': str(appointment_id),
                'date': normalized_date,
                'time': normalized_time,
                'purpose': purpose
            }
            
            logger.info(f"✅ Appointment booked: {normalized_date} {normalized_time}")
            
            response = (
                f"Perfect! You're all set for tomorrow at {self._format_time_ampm(normalized_time)}. "
                "Anything else?"
            )
            
            await self._send_tool_call_event(context, "book_appointment", 
                {"date": normalized_date, "time": normalized_time, "purpose": purpose}, response)
            await self._say_response(context, response)
            return None
            
        except Exception as e:
            logger.error(f"❌ Error booking appointment: {e}", exc_info=True)
            response = "Sorry, couldn't book that. Try a different time?"
            await self._say_response(context, response)
            return None

    @function_tool
    async def retrieve_appointments(self, context: RunContext) -> str:
        """Retrieve all appointments for the identified user.
        """
        logger.info(f"📋 retrieve_appointments")
        
        if not self.context.user_id:
            logger.warning("⚠️  Cannot retrieve appointments: User not identified")
            response = "I need to identify you first. Could you please provide your phone number?"
            await self._say_response(context, response)
            return None
        
        try:
            appointments = await self.db.get_user_appointments(self.context.user_id)
            
            if not appointments:
                logger.debug(f"ℹ️  No appointments found")
                response = "You don't have any appointments scheduled. Would you like to book one?"
                await self._send_tool_call_event(context, "retrieve_appointments", {}, response)
                await self._say_response(context, response)
                return None
            
            # Separate upcoming and past appointments
            now = datetime.utcnow()
            upcoming = []
            past = []
            
            for apt in appointments:
                if apt['datetime'] > now and apt['status'] != 'cancelled':
                    upcoming.append(apt)
                else:
                    past.append(apt)
            
            response_parts = []
            
            if upcoming:
                logger.info(f"✅ Found {len(upcoming)} appointments")
                response_parts.append("Your upcoming appointments:")
                for apt in upcoming[:3]:  # Limit to 3 for brevity
                    formatted_date = apt['datetime'].strftime("%A, %B %d at %I:%M %p")
                    response_parts.append(f"{formatted_date} for {apt['purpose']}")
            
            response = " ".join(response_parts) + ". Need to change anything?"
            
            await self._send_tool_call_event(context, "retrieve_appointments", 
                {"count": len(appointments)}, response)
            await self._say_response(context, response)
            return None
            
        except Exception as e:
            logger.error(f"❌ Error retrieving appointments: {e}", exc_info=True)
            response = "I'm having trouble accessing your appointments right now. Please try again in a moment."
            await self._say_response(context, response)
            return None

    @function_tool
    async def cancel_appointment(self, context: RunContext, appointment_id: str = None, date: str = None, time: str = None) -> str:
        """Cancel an appointment by ID or date/time.
        
        Args:
            appointment_id: The appointment ID to cancel
            date: Appointment date (YYYY-MM-DD format) 
            time: Appointment time (HH:MM format)
        """
        logger.info(f"❌ cancel_appointment: {appointment_id or f'{date} {time}'}")
        
        if not self.context.user_id:
            logger.warning("⚠️  Cannot cancel appointment: User not identified")
            response = "I need to identify you first. Could you please provide your phone number?"
            await self._say_response(context, response)
            return None
        
        try:
            appointment = None
            
            if appointment_id:
                appointment = await self.db.get_appointment_by_id(appointment_id, self.context.user_id)
            elif date and time:
                appointment = await self.db.get_appointment_by_datetime(self.context.user_id, date, time)
            else:
                response = "I need either the appointment ID or the date and time to cancel an appointment."
                await self._say_response(context, response)
                return None
            
            if not appointment:
                response = "I couldn't find that appointment. Could you please check the details and try again?"
                await self._send_tool_call_event(context, "cancel_appointment", 
                    {"appointment_id": appointment_id, "date": date, "time": time}, response)
                await self._say_response(context, response)
                return None
            
            if appointment['status'] == 'cancelled':
                response = "That appointment is already cancelled."
                await self._send_tool_call_event(context, "cancel_appointment", 
                    {"appointment_id": appointment_id, "date": date, "time": time}, response)
                await self._say_response(context, response)
                return None
            
            # Cancel the appointment
            await self.db.update_appointment_status(appointment['_id'], 'cancelled')
            
            formatted_date = appointment['datetime'].strftime("%A, %B %d at %I:%M %p")
            logger.info(f"✅ Appointment cancelled")
            
            response = f"I've cancelled your appointment on {formatted_date}. Anything else?"
            await self._send_tool_call_event(context, "cancel_appointment", 
                {"date": date, "time": time}, response)
            await self._say_response(context, response)
            return None
            
        except Exception as e:
            logger.error(f"❌ Error cancelling appointment: {e}", exc_info=True)
            response = "I'm sorry, I couldn't cancel that appointment right now. Please try again."
            await self._say_response(context, response)
            return None

    @function_tool
    async def modify_appointment(self, context: RunContext, appointment_id: str, new_date: str = None, new_time: str = None, new_purpose: str = None) -> str:
        """Modify an existing appointment.
        
        Args:
            appointment_id: The appointment ID to modify
            new_date: New date (YYYY-MM-DD format)
            new_time: New time (HH:MM format)  
            new_purpose: New purpose for the appointment
        """
        logger.info(f"✏️  modify_appointment: {appointment_id}")
        
        if not self.context.user_id:
            logger.warning("⚠️  Cannot modify appointment: User not identified")
            response = "I need to identify you first. Could you please provide your phone number?"
            await self._say_response(context, response)
            return None
        
        try:
            appointment = await self.db.get_appointment_by_id(appointment_id, self.context.user_id)
            
            if not appointment:
                response = "I couldn't find that appointment. Could you please check the appointment ID?"
                await self._send_tool_call_event(context, "modify_appointment", 
                    {"appointment_id": appointment_id}, response)
                await self._say_response(context, response)
                return None
            
            if appointment['status'] == 'cancelled':
                response = "That appointment is cancelled and cannot be modified. Would you like to book a new one?"
                await self._send_tool_call_event(context, "modify_appointment", 
                    {"appointment_id": appointment_id}, response)
                await self._say_response(context, response)
                return None
            
            updates = {}
            
            if new_date and new_time:
                # Check if new slot is available
                datetime_str = f"{new_date} {new_time}"
                booked_slots = await self.db.get_booked_slots(new_date)
                
                if datetime_str in booked_slots:
                    response = f"Sorry, {new_time} on {new_date} is already booked. Please choose a different time."
                    await self._send_tool_call_event(context, "modify_appointment", 
                        {"appointment_id": appointment_id, "new_date": new_date, "new_time": new_time}, response)
                    await self._say_response(context, response)
                    return None
                
                updates['date'] = new_date
                updates['time'] = new_time
                updates['datetime'] = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
            
            if new_purpose:
                updates['purpose'] = new_purpose
            
            if not updates:
                response = "What would you like to change about your appointment? The date, time, or purpose?"
                await self._say_response(context, response)
                return None
            
            # Update the appointment
            await self.db.update_appointment(appointment['_id'], updates)
            
            logger.info(f"✅ Appointment modified")
            
            if 'datetime' in updates:
                new_date_formatted = updates['datetime'].strftime("%A, %B %d at %I:%M %p")
                response = f"Updated! Your appointment is now {new_date_formatted}."
            else:
                response = f"Updated your appointment purpose to {updates['purpose']}."
            
            await self._send_tool_call_event(context, "modify_appointment", 
                {"appointment_id": appointment_id, "updates": updates}, response)
            await self._say_response(context, response)
            return None
            
        except Exception as e:
            logger.error(f"❌ Error modifying appointment: {e}", exc_info=True)
            response = "I'm sorry, I couldn't modify that appointment right now. Please try again."
            await self._say_response(context, response)
            return None

    @function_tool
    async def end_conversation(self, context: RunContext) -> str:
        """End the conversation and generate a summary.
        """
        logger.info("👋 end_conversation")
        
        try:
            # Generate conversation summary
            summary_data = {
                'user_id': self.context.user_id,
                'user_phone': self.context.user_phone,
                'conversation_date': datetime.utcnow(),
                'appointments_discussed': [],
                'user_preferences': [],
                'summary_text': ""
            }
            
            # Add any appointments from this conversation
            if self.context.pending_appointment:
                summary_data['appointments_discussed'].append(self.context.pending_appointment)
            
            # Generate summary text
            summary_parts = [
                f"Conversation with {self.context.user_name or 'User'} on {datetime.now().strftime('%B %d, %Y')}"
            ]
            
            if self.context.pending_appointment:
                apt = self.context.pending_appointment
                summary_parts.append(f"Booked appointment: {apt['date']} at {apt['time']} for {apt['purpose']}")
            
            summary_data['summary_text'] = ". ".join(summary_parts)
            
            # Save summary to database
            if self.context.user_id:
                await self.db.save_conversation_summary(summary_data)
                logger.debug(f"✅ Conversation summary saved")
            else:
                logger.warning("⚠️  No user ID available, skipping summary save")
            
            # Send summary to frontend
            summary_event = {
                "type": "conversation_summary",
                "summary": summary_data
            }
            await self._publish_data_event(context, summary_event)

            # Signal frontend to end the call after showing summary
            await self._publish_data_event(context, {"type": "end_call"})
            
            response = "Thank you for using our appointment booking service! Have a great day!"
            await self._say_response(context, response)
            logger.info(
                "Final context | user=%s | agent=%s | tool=%s",
                self.context.last_user_message,
                self.context.last_agent_message,
                self.context.last_tool_call,
            )
            return None
            
        except Exception as e:
            logger.error(f"❌ Error ending conversation: {e}", exc_info=True)
            response = "Thank you for using our appointment booking service! Have a great day!"
            await self._say_response(context, response)
            logger.info(
                "Final context | user=%s | agent=%s | tool=%s",
                self.context.last_user_message,
                self.context.last_agent_message,
                self.context.last_tool_call,
            )
            return None
