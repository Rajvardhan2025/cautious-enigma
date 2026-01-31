import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from livekit.agents import (
    Agent,
    RunContext,
    function_tool,
)

from core.database import DatabaseManager
from core.models import Appointment

logger = logging.getLogger("agent.tools")




@dataclass
class ConversationContext:
    user_id: Optional[str] = None
    user_phone: Optional[str] = None
    user_name: Optional[str] = None
    conversation_history: List[Dict] = None
    pending_appointment: Optional[Dict] = None
    
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
- Wait for user responses before continuing

Your job:
1. Get phone number to identify user
2. Help book, view, modify, or cancel appointments
3. Confirm details clearly and briefly

When booking:
- Ask for date, then time, then purpose (one at a time)
- Confirm briefly: "Got it, booked for [day] at [time]"
- Don't read appointment IDs or technical details

Be warm, brief, and helpful.""",
        )
        logger.info("🤖 VoiceAppointmentAgent initialized")
        self.db = DatabaseManager()
        self.context = ConversationContext()
        logger.info("✅ Database manager and conversation context ready")

    async def _send_tool_call_event(self, context: RunContext, tool_name: str, parameters: Dict, result: str):
        """Send tool call event to frontend for display"""
        try:
            import json
            event_data = {
                "type": "tool_call",
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success"
            }
            
            # Send to room via data channel
            if hasattr(context, 'room') and context.room:
                await context.room.local_participant.publish_data(
                    json.dumps(event_data).encode('utf-8'),
                    reliable=True
                )
                logger.info(f"📤 Sent tool call event to frontend: {tool_name}")
            else:
                logger.warning(f"⚠️  No room context available to send tool call event")
        except Exception as e:
            logger.error(f"❌ Error sending tool call event: {e}", exc_info=True)

    @function_tool
    async def identify_user(self, context: RunContext, phone_number: str) -> str:
        """Identify a user by their phone number.
        
        Args:
            phone_number: The user's phone number for identification
        """
        logger.info(f"🔍 Tool called: identify_user with phone: {phone_number}")
        
        try:
            # Clean phone number
            clean_phone = ''.join(filter(str.isdigit, phone_number))
            
            user = await self.db.get_user_by_phone(clean_phone)
            if user:
                self.context.user_id = str(user['_id'])
                self.context.user_phone = clean_phone
                self.context.user_name = user.get('name', 'User')
                
                logger.info(f"✅ User identified: {self.context.user_name} (ID: {self.context.user_id})")
                response = f"Hi {self.context.user_name}! How can I help you today?"
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
                
                logger.info(f"✅ New user created with ID: {user_id}")
                response = "Welcome! What's your name?"
            
            # Send tool call event to frontend
            await self._send_tool_call_event(context, "identify_user", {"phone_number": phone_number}, response)
            return response
                
        except Exception as e:
            logger.error(f"❌ Error identifying user: {e}", exc_info=True)
            response = "Sorry, I couldn't find that number. Can you try again?"
            return response

    @function_tool
    async def fetch_slots(self, context: RunContext, date: str = None) -> str:
        """Fetch available appointment slots for a given date.
        
        Args:
            date: Date to check slots for (YYYY-MM-DD format). If not provided, shows next 7 days.
        """
        logger.info(f"📅 Tool called: fetch_slots for date: {date or 'next 7 days'}")
        
        try:
            # Hard-coded available slots (9 AM to 5 PM, hourly)
            base_slots = [
                "09:00", "10:00", "11:00", "12:00", 
                "13:00", "14:00", "15:00", "16:00", "17:00"
            ]
            
            if date:
                # Get booked slots for the specific date
                booked_slots = await self.db.get_booked_slots(date)
                available_slots = [slot for slot in base_slots if f"{date} {slot}" not in booked_slots]
                
                if available_slots:
                    # Only mention first few slots to keep it brief
                    slots_preview = ", ".join(available_slots[:4])
                    more = f" and {len(available_slots) - 4} more" if len(available_slots) > 4 else ""
                    response = f"I have {slots_preview}{more}. Which works for you?"
                else:
                    response = f"No slots available on {date}. Try another day?"
            else:
                # Show next 7 days with availability
                today = datetime.now().date()
                available_count = 0
                
                for i in range(7):
                    check_date = today + timedelta(days=i)
                    date_str = check_date.strftime("%Y-%m-%d")
                    booked_slots = await self.db.get_booked_slots(date_str)
                    day_available = len([slot for slot in base_slots if f"{date_str} {slot}" not in booked_slots])
                    
                    if day_available > 0:
                        available_count += 1
                
                if available_count > 0:
                    response = f"I have openings this week. What day works for you?"
                else:
                    response = "This week is full. Want to check next week?"
            
            await self._send_tool_call_event(context, "fetch_slots", {"date": date}, response)
            return response
                    
        except Exception as e:
            logger.error(f"❌ Error fetching slots: {e}", exc_info=True)
            response = "Can't check slots right now. Try again?"
            return response

    @function_tool
    async def book_appointment(self, context: RunContext, date: str, time: str, purpose: str = "General consultation") -> str:
        """Book an appointment for the identified user.
        
        Args:
            date: Appointment date (YYYY-MM-DD format)
            time: Appointment time (HH:MM format)
            purpose: Purpose or reason for the appointment
        """
        logger.info(f"📝 Tool called: book_appointment for {self.context.user_phone}: {date} {time} - {purpose}")
        
        if not self.context.user_id:
            logger.warning("⚠️  Cannot book appointment: User not identified")
            return "I need your phone number first."
        
        try:
            # Check if slot is available
            datetime_str = f"{date} {time}"
            booked_slots = await self.db.get_booked_slots(date)
            
            if datetime_str in booked_slots:
                logger.warning(f"⚠️  Slot {datetime_str} is already booked")
                response = f"Sorry, {time} on {date} is taken. Want a different time?"
                await self._send_tool_call_event(context, "book_appointment", 
                    {"date": date, "time": time, "purpose": purpose}, response)
                return response
            
            # Create appointment
            appointment_data = {
                'user_id': self.context.user_id,
                'date': date,
                'time': time,
                'datetime': datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M"),
                'purpose': purpose,
                'status': 'confirmed',
                'created_at': datetime.utcnow()
            }
            
            appointment_id = await self.db.create_appointment(appointment_data)
            
            # Store in context for summary
            self.context.pending_appointment = {
                'id': str(appointment_id),
                'date': date,
                'time': time,
                'purpose': purpose
            }
            
            logger.info(f"✅ Appointment booked successfully: {appointment_id} for user {self.context.user_id}")
            
            formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%A, %B %d")
            response = f"Perfect! You're all set for {formatted_date} at {time}. Anything else?"
            
            await self._send_tool_call_event(context, "book_appointment", 
                {"date": date, "time": time, "purpose": purpose}, response)
            return response
            
        except Exception as e:
            logger.error(f"❌ Error booking appointment: {e}", exc_info=True)
            response = "Sorry, couldn't book that. Try a different time?"
            return response

    @function_tool
    async def retrieve_appointments(self, context: RunContext) -> str:
        """Retrieve all appointments for the identified user.
        """
        logger.info(f"📋 Tool called: retrieve_appointments for user: {self.context.user_id}")
        
        if not self.context.user_id:
            logger.warning("⚠️  Cannot retrieve appointments: User not identified")
            response = "I need to identify you first. Could you please provide your phone number?"
            return response
        
        try:
            appointments = await self.db.get_user_appointments(self.context.user_id)
            
            if not appointments:
                logger.info(f"ℹ️  No appointments found for user {self.context.user_id}")
                response = "You don't have any appointments scheduled. Would you like to book one?"
                await self._send_tool_call_event(context, "retrieve_appointments", {}, response)
                return response
            
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
                logger.info(f"✅ Found {len(upcoming)} upcoming appointments for user {self.context.user_id}")
                response_parts.append("Your upcoming appointments:")
                for apt in upcoming[:3]:  # Limit to 3 for brevity
                    formatted_date = apt['datetime'].strftime("%A, %B %d at %I:%M %p")
                    response_parts.append(f"{formatted_date} for {apt['purpose']}")
            
            response = " ".join(response_parts) + ". Need to change anything?"
            
            await self._send_tool_call_event(context, "retrieve_appointments", 
                {"count": len(appointments)}, response)
            return response
            
        except Exception as e:
            logger.error(f"❌ Error retrieving appointments: {e}", exc_info=True)
            response = "I'm having trouble accessing your appointments right now. Please try again in a moment."
            return response

    @function_tool
    async def cancel_appointment(self, context: RunContext, appointment_id: str = None, date: str = None, time: str = None) -> str:
        """Cancel an appointment by ID or date/time.
        
        Args:
            appointment_id: The appointment ID to cancel
            date: Appointment date (YYYY-MM-DD format) 
            time: Appointment time (HH:MM format)
        """
        logger.info(f"❌ Tool called: cancel_appointment - ID={appointment_id}, date={date}, time={time}")
        
        if not self.context.user_id:
            logger.warning("⚠️  Cannot cancel appointment: User not identified")
            response = "I need to identify you first. Could you please provide your phone number?"
            return response
        
        try:
            appointment = None
            
            if appointment_id:
                appointment = await self.db.get_appointment_by_id(appointment_id, self.context.user_id)
            elif date and time:
                appointment = await self.db.get_appointment_by_datetime(self.context.user_id, date, time)
            else:
                response = "I need either the appointment ID or the date and time to cancel an appointment."
                return response
            
            if not appointment:
                response = "I couldn't find that appointment. Could you please check the details and try again?"
                await self._send_tool_call_event(context, "cancel_appointment", 
                    {"appointment_id": appointment_id, "date": date, "time": time}, response)
                return response
            
            if appointment['status'] == 'cancelled':
                response = "That appointment is already cancelled."
                await self._send_tool_call_event(context, "cancel_appointment", 
                    {"appointment_id": appointment_id, "date": date, "time": time}, response)
                return response
            
            # Cancel the appointment
            await self.db.update_appointment_status(appointment['_id'], 'cancelled')
            
            formatted_date = appointment['datetime'].strftime("%A, %B %d at %I:%M %p")
            logger.info(f"✅ Appointment cancelled successfully: {appointment['_id']}")
            
            response = f"I've cancelled your appointment on {formatted_date}. Anything else?"
            await self._send_tool_call_event(context, "cancel_appointment", 
                {"date": date, "time": time}, response)
            return response
            
        except Exception as e:
            logger.error(f"❌ Error cancelling appointment: {e}", exc_info=True)
            response = "I'm sorry, I couldn't cancel that appointment right now. Please try again."
            return response

    @function_tool
    async def modify_appointment(self, context: RunContext, appointment_id: str, new_date: str = None, new_time: str = None, new_purpose: str = None) -> str:
        """Modify an existing appointment.
        
        Args:
            appointment_id: The appointment ID to modify
            new_date: New date (YYYY-MM-DD format)
            new_time: New time (HH:MM format)  
            new_purpose: New purpose for the appointment
        """
        logger.info(f"✏️  Tool called: modify_appointment - ID={appointment_id}, new_date={new_date}, new_time={new_time}, new_purpose={new_purpose}")
        
        if not self.context.user_id:
            logger.warning("⚠️  Cannot modify appointment: User not identified")
            response = "I need to identify you first. Could you please provide your phone number?"
            return response
        
        try:
            appointment = await self.db.get_appointment_by_id(appointment_id, self.context.user_id)
            
            if not appointment:
                response = "I couldn't find that appointment. Could you please check the appointment ID?"
                await self._send_tool_call_event(context, "modify_appointment", 
                    {"appointment_id": appointment_id}, response)
                return response
            
            if appointment['status'] == 'cancelled':
                response = "That appointment is cancelled and cannot be modified. Would you like to book a new one?"
                await self._send_tool_call_event(context, "modify_appointment", 
                    {"appointment_id": appointment_id}, response)
                return response
            
            updates = {}
            
            if new_date and new_time:
                # Check if new slot is available
                datetime_str = f"{new_date} {new_time}"
                booked_slots = await self.db.get_booked_slots(new_date)
                
                if datetime_str in booked_slots:
                    response = f"Sorry, {new_time} on {new_date} is already booked. Please choose a different time."
                    await self._send_tool_call_event(context, "modify_appointment", 
                        {"appointment_id": appointment_id, "new_date": new_date, "new_time": new_time}, response)
                    return response
                
                updates['date'] = new_date
                updates['time'] = new_time
                updates['datetime'] = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
            
            if new_purpose:
                updates['purpose'] = new_purpose
            
            if not updates:
                response = "What would you like to change about your appointment? The date, time, or purpose?"
                return response
            
            # Update the appointment
            await self.db.update_appointment(appointment['_id'], updates)
            
            logger.info(f"✅ Appointment modified successfully: {appointment['_id']}")
            
            if 'datetime' in updates:
                new_date_formatted = updates['datetime'].strftime("%A, %B %d at %I:%M %p")
                response = f"Updated! Your appointment is now {new_date_formatted}."
            else:
                response = f"Updated your appointment purpose to {updates['purpose']}."
            
            await self._send_tool_call_event(context, "modify_appointment", 
                {"appointment_id": appointment_id, "updates": updates}, response)
            return response
            
        except Exception as e:
            logger.error(f"❌ Error modifying appointment: {e}", exc_info=True)
            response = "I'm sorry, I couldn't modify that appointment right now. Please try again."
            return response

    @function_tool
    async def end_conversation(self, context: RunContext) -> str:
        """End the conversation and generate a summary.
        """
        logger.info("👋 Tool called: end_conversation - Generating summary")
        
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
                logger.info(f"✅ Conversation summary saved for user {self.context.user_id}")
            else:
                logger.warning("⚠️  No user ID available, skipping summary save")
            
            # Send summary to frontend
            import json
            summary_event = {
                "type": "conversation_summary",
                "summary": summary_data
            }
            
            if hasattr(context, 'room') and context.room:
                await context.room.local_participant.publish_data(
                    json.dumps(summary_event, default=str).encode('utf-8'),
                    reliable=True
                )
            
            response = "Thank you for using our appointment booking service! Have a great day!"
            return response
            
        except Exception as e:
            logger.error(f"❌ Error ending conversation: {e}", exc_info=True)
            response = "Thank you for using our appointment booking service! Have a great day!"
            return response
