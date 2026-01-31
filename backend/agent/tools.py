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
        self.db = DatabaseManager()
        self.context = ConversationContext()

    @function_tool
    async def identify_user(self, context: RunContext, phone_number: str) -> str:
        """Identify a user by their phone number.
        
        Args:
            phone_number: The user's phone number for identification
        """
        logger.info(f"Identifying user with phone: {phone_number}")
        
        try:
            # Clean phone number
            clean_phone = ''.join(filter(str.isdigit, phone_number))
            
            user = await self.db.get_user_by_phone(clean_phone)
            if user:
                self.context.user_id = str(user['_id'])
                self.context.user_phone = clean_phone
                self.context.user_name = user.get('name', 'User')
                
                logger.info(f"User identified: {self.context.user_name}")
                return f"Hi {self.context.user_name}! How can I help you today?"
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
                
                logger.info(f"New user created: {user_id}")
                return "Welcome! What's your name?"
                
        except Exception as e:
            logger.error(f"Error identifying user: {e}")
            return "Sorry, I couldn't find that number. Can you try again?"

    @function_tool
    async def fetch_slots(self, context: RunContext, date: str = None) -> str:
        """Fetch available appointment slots for a given date.
        
        Args:
            date: Date to check slots for (YYYY-MM-DD format). If not provided, shows next 7 days.
        """
        logger.info(f"Fetching available slots for date: {date}")
        
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
                    return f"I have {slots_preview}{more}. Which works for you?"
                else:
                    return f"No slots available on {date}. Try another day?"
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
                    return f"I have openings this week. What day works for you?"
                else:
                    return "This week is full. Want to check next week?"
                    
        except Exception as e:
            logger.error(f"Error fetching slots: {e}")
            return "Can't check slots right now. Try again?"

    @function_tool
    async def book_appointment(self, context: RunContext, date: str, time: str, purpose: str = "General consultation") -> str:
        """Book an appointment for the identified user.
        
        Args:
            date: Appointment date (YYYY-MM-DD format)
            time: Appointment time (HH:MM format)
            purpose: Purpose or reason for the appointment
        """
        logger.info(f"Booking appointment for {self.context.user_phone}: {date} {time}")
        
        if not self.context.user_id:
            return "I need your phone number first."
        
        try:
            # Check if slot is available
            datetime_str = f"{date} {time}"
            booked_slots = await self.db.get_booked_slots(date)
            
            if datetime_str in booked_slots:
                return f"Sorry, {time} on {date} is taken. Want a different time?"
            
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
            
            logger.info(f"Appointment booked successfully: {appointment_id}")
            
            formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%A, %B %d")
            return f"Perfect! You're all set for {formatted_date} at {time}. Anything else?"
            
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            return "Sorry, couldn't book that. Try a different time?"

    @function_tool
    async def retrieve_appointments(self, context: RunContext) -> str:
        """Retrieve all appointments for the identified user.
        """
        logger.info(f"Retrieving appointments for user: {self.context.user_id}")
        
        if not self.context.user_id:
            return "I need to identify you first. Could you please provide your phone number?"
        
        try:
            appointments = await self.db.get_user_appointments(self.context.user_id)
            
            if not appointments:
                return "You don't have any appointments scheduled. Would you like to book one?"
            
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
                response_parts.append("Your upcoming appointments:")
                for apt in upcoming[:5]:  # Limit to 5 most recent
                    formatted_date = apt['datetime'].strftime("%A, %B %d at %I:%M %p")
                    response_parts.append(f"- {formatted_date}: {apt['purpose']}")
            
            if past:
                response_parts.append("Your recent past appointments:")
                for apt in sorted(past, key=lambda x: x['datetime'], reverse=True)[:3]:
                    formatted_date = apt['datetime'].strftime("%B %d at %I:%M %p")
                    response_parts.append(f"- {formatted_date}: {apt['purpose']}")
            
            return " ".join(response_parts) + " Would you like to modify any of these or book a new appointment?"
            
        except Exception as e:
            logger.error(f"Error retrieving appointments: {e}")
            return "I'm having trouble accessing your appointments right now. Please try again in a moment."

    @function_tool
    async def cancel_appointment(self, context: RunContext, appointment_id: str = None, date: str = None, time: str = None) -> str:
        """Cancel an appointment by ID or date/time.
        
        Args:
            appointment_id: The appointment ID to cancel
            date: Appointment date (YYYY-MM-DD format) 
            time: Appointment time (HH:MM format)
        """
        logger.info(f"Cancelling appointment: ID={appointment_id}, date={date}, time={time}")
        
        if not self.context.user_id:
            return "I need to identify you first. Could you please provide your phone number?"
        
        try:
            appointment = None
            
            if appointment_id:
                appointment = await self.db.get_appointment_by_id(appointment_id, self.context.user_id)
            elif date and time:
                appointment = await self.db.get_appointment_by_datetime(self.context.user_id, date, time)
            else:
                return "I need either the appointment ID or the date and time to cancel an appointment."
            
            if not appointment:
                return "I couldn't find that appointment. Could you please check the details and try again?"
            
            if appointment['status'] == 'cancelled':
                return "That appointment is already cancelled."
            
            # Cancel the appointment
            await self.db.update_appointment_status(appointment['_id'], 'cancelled')
            
            formatted_date = appointment['datetime'].strftime("%A, %B %d at %I:%M %p")
            logger.info(f"Appointment cancelled: {appointment['_id']}")
            
            return f"I've cancelled your appointment on {formatted_date} for {appointment['purpose']}. Is there anything else I can help you with?"
            
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            return "I'm sorry, I couldn't cancel that appointment right now. Please try again."

    @function_tool
    async def modify_appointment(self, context: RunContext, appointment_id: str, new_date: str = None, new_time: str = None, new_purpose: str = None) -> str:
        """Modify an existing appointment.
        
        Args:
            appointment_id: The appointment ID to modify
            new_date: New date (YYYY-MM-DD format)
            new_time: New time (HH:MM format)  
            new_purpose: New purpose for the appointment
        """
        logger.info(f"Modifying appointment {appointment_id}")
        
        if not self.context.user_id:
            return "I need to identify you first. Could you please provide your phone number?"
        
        try:
            appointment = await self.db.get_appointment_by_id(appointment_id, self.context.user_id)
            
            if not appointment:
                return "I couldn't find that appointment. Could you please check the appointment ID?"
            
            if appointment['status'] == 'cancelled':
                return "That appointment is cancelled and cannot be modified. Would you like to book a new one?"
            
            updates = {}
            
            if new_date and new_time:
                # Check if new slot is available
                datetime_str = f"{new_date} {new_time}"
                booked_slots = await self.db.get_booked_slots(new_date)
                
                if datetime_str in booked_slots:
                    return f"Sorry, the {new_time} slot on {new_date} is already booked. Please choose a different time."
                
                updates['date'] = new_date
                updates['time'] = new_time
                updates['datetime'] = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
            
            if new_purpose:
                updates['purpose'] = new_purpose
            
            if not updates:
                return "What would you like to change about your appointment? The date, time, or purpose?"
            
            # Update the appointment
            await self.db.update_appointment(appointment['_id'], updates)
            
            old_date = appointment['datetime'].strftime("%A, %B %d at %I:%M %p")
            if 'datetime' in updates:
                new_date_formatted = updates['datetime'].strftime("%A, %B %d at %I:%M %p")
                return f"I've updated your appointment from {old_date} to {new_date_formatted}. The purpose is {updates.get('purpose', appointment['purpose'])}."
            else:
                return f"I've updated your appointment on {old_date}. The purpose is now {updates['purpose']}."
            
        except Exception as e:
            logger.error(f"Error modifying appointment: {e}")
            return "I'm sorry, I couldn't modify that appointment right now. Please try again."

    @function_tool
    async def end_conversation(self, context: RunContext) -> str:
        """End the conversation and generate a summary.
        """
        logger.info("Ending conversation and generating summary")
        
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
            
            logger.info("Conversation summary saved")
            
            return "Thank you for using our appointment booking service! I've saved a summary of our conversation. Have a great day!"
            
        except Exception as e:
            logger.error(f"Error ending conversation: {e}")
            return "Thank you for using our appointment booking service! Have a great day!"
