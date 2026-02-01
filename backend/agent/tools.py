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
from core.summary_service import ConversationTracker, SummaryGenerator

logger = logging.getLogger("agent.tools")

ALLOWED_TIMES = ["12:00", "15:00", "17:00", "18:00", "19:00"]




@dataclass
class ConversationContext:
    user_id: Optional[str] = None
    user_phone: Optional[str] = None
    user_name: Optional[str] = None
    user_preferences: List[str] = None
    conversation_history: List[Dict] = None
    pending_appointment: Optional[Dict] = None
    last_user_message: Optional[str] = None
    last_agent_message: Optional[str] = None
    last_tool_call: Optional[Dict] = None
    
    # Add conversation tracker for enhanced summaries
    tracker: Optional[ConversationTracker] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.user_preferences is None:
            self.user_preferences = []
        if self.tracker is None:
            self.tracker = ConversationTracker()


class VoiceAppointmentAgent(Agent):
    def __init__(self, user_context: Optional[Dict] = None) -> None:
        # Initialize conversation context with tracker
        self.context = ConversationContext()
        
        # Build instructions with optional user context
        base_instructions = """# Identity

You are Alya, a friendly and efficient appointment booking assistant for a medical clinic. Your primary role is to help users schedule, view, modify, and cancel appointments through natural voice conversation.

# Core Responsibilities

1. **Identify the User**: You must identify the user by phone number before accessing or creating records.
2. **Context Persistence**: If a user asks to do something (e.g., "See my appointments") but you need to identify them first, **you must remember their original request** and fulfill it immediately after identification matches.
3. **Appointment Management**: Book, view, modify, or cancel appointments.
   - **Booking is ONLY available for TOMORROW.**
   - **Available slots**: 12 PM, 3 PM, 5 PM, 6 PM, 7 PM.

# Conversation Flow Guidelines

1. **Start**: Greet the user or handle their immediate request.
2. **Missing Info**: If you need information (like phone number) to complete a request, ask for it.
3. **After Tool Execution**:
   - If `identify_user` completes successfully: **Check the conversation history.**
     - Did the user ask to see appointments? -> Call `retrieve_appointments`.
     - Did the user ask to book? -> Call `book_appointment` or ask for time if missing.
     - Did the user just say "Hello"? -> Ask how you can help.
   - Do NOT simply restart the "Booking" script. React to the user's actual intent.
4. **Name Collection**: If the user's name is missing (Result is 'User'), ask for it gently ("Could I get your name to personalize your account?"). After saving it, **resume the previous task**.

# Output Style

- **Natural**: Speak like a human. "Tomorrow", "12 PM".
- **Concise**: Keep responses under 2 sentences.
- **Proactive**: If a task is finished, ask "Anything else?"

# Important Rules

- **Don't Loop**: If you just welcomed the user, don't welcome them again.
- **Don't Force Booking**: If the user wants to *view* appointments, do not ask "What time works for you?". Just show the appointments.
- **One Question at a Time**: Don't bombard the user.
- **No Hallucinations**: You do NOT have capabilities to:
  - Set reminders or alarms.
  - Send SMS or emails.
  - Access external calendars.
  - Provide medical advice.
  If a user asks for these, politely explain you cant do that and return to appointment management.

# After Identifying User or Setting Name
- IMMEDIATELY check the conversation history for any pending request (e.g., "Book for 6 PM").
- If a request is pending and you have all details, EXECUTE IT immediately. Do not ask "What would you like to do?" again.
- If you don't have a pending request, THEN ask how you can help.
"""



        # Add user information section if provided
        if user_context:
            user_info_parts = ["\n\n# User Information\n"]
            if user_context.get("name"):
                user_info_parts.append(f"- User's name: {user_context['name']}")
            if user_context.get("phone"):
                user_info_parts.append(f"- Phone number: {user_context['phone']}")
            if user_context.get("preferences"):
                user_info_parts.append(f"- Preferences: {', '.join(user_context['preferences'])}")
            if user_context.get("upcoming_appointments"):
                user_info_parts.append(f"- Has {user_context['upcoming_appointments']} upcoming appointment(s)")
            
            base_instructions += "\n".join(user_info_parts)

        super().__init__(instructions=base_instructions)
        self.db = DatabaseManager()
        self.context = ConversationContext()

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
                logger.debug("[DataEvent] No room context available")
                return

            await room.local_participant.publish_data(
                json.dumps(payload, default=str).encode("utf-8"),
                reliable=True,
            )
        except Exception as e:
            logger.error(f"[DataEvent] Error: {e}")

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
        logger.debug(f"[Tool] {tool_name} | {parameters}")

    async def _say_response(self, context: RunContext, text: str) -> None:
        """Speak the tool response verbatim to avoid LLM paraphrasing."""
        try:
            session = getattr(context, "session", None)
            if session:
                await session.say(text, allow_interruptions=True)
                self.context.last_agent_message = text
        except Exception as e:
            logger.error(f"[Speech] Error: {e}")

    @function_tool
    async def identify_user(self, context: RunContext, phone_number: str) -> str:
        """Identify a user by their phone number.
        
        Args:
            phone_number: The user's phone number for identification
        """
        logger.debug(f"[identify_user] {phone_number}")
        
        try:
            # Clean phone number
            clean_phone = ''.join(filter(str.isdigit, phone_number))
            
            user = await self.db.get_user_by_phone(clean_phone)
            if user:
                self.context.user_id = str(user['_id'])
                self.context.user_phone = clean_phone
                self.context.user_name = user.get('name') or 'User'
                
                # Track user identification
                self.context.tracker.user_id = self.context.user_id
                self.context.tracker.user_phone = clean_phone
                self.context.tracker.user_name = self.context.user_name
                self.context.tracker.add_event('user_identified', {
                    'returning_user': True,
                    'has_name': bool(user.get('name'))
                })
                
                if not user.get('name') or user.get('name') == 'User':
                    # Fallthrough to logic below
                    pass
                else:
                    # Fallthrough to logic below
                    pass
            else:
                # Create new user
                user_data = {
                    'phone': clean_phone,
                    'name': None,
                    'created_at': datetime.utcnow()
                }
                user_id = await self.db.create_user(user_data)
                self.context.user_id = str(user_id)
                self.context.user_phone = clean_phone
                self.context.user_name = 'User'
                
                # Track new user creation
                self.context.tracker.user_id = self.context.user_id
                self.context.tracker.user_phone = clean_phone
                self.context.tracker.user_name = 'User'
                self.context.tracker.add_event('user_identified', {
                    'returning_user': False,
                    'new_user_created': True
                })
                
            # Determine response for UI and LLM
            has_name = self.context.user_name and self.context.user_name != 'User'
            
            if has_name:
                ui_response = f"Welcome back, {self.context.user_name}!"
                llm_response = f"User identified as {self.context.user_name}. Check conversation history for pending requests."
            else:
                ui_response = "Thanks! Could I get your name?"
                llm_response = "User identified but name is missing. Ask for name."
            
            # Send tool call event to frontend with UI-friendly message
            await self._send_tool_call_event(context, "identify_user", {"phone_number": phone_number}, ui_response)
            
            # Return system status to LLM (do not speak directly)
            return llm_response
                
        except Exception as e:
            logger.error(f"[identify_user] Error: {e}")
            response = "Sorry, I couldn't find that number. Can you try again?"
            await self._say_response(context, response)
            return response

    @function_tool
    async def set_user_name(self, context: RunContext, name: str) -> str:
        """Save the user's name for personalization and summaries.

        Args:
            name: The user's name
        """
        logger.debug(f"[set_user_name] {name}")

        try:
            clean_name = name.strip()
            if not clean_name:
                response = "Sorry, I didn't catch your name. What should I call you?"
                await self._say_response(context, response)
                return None

            self.context.user_name = clean_name
            if self.context.user_id:
                await self.db.update_user(self.context.user_id, {"name": clean_name})
            
            # Track name update
            self.context.tracker.user_name = clean_name
            self.context.tracker.add_event('name_saved', {'name': clean_name})

            ui_response = f"Thanks, {clean_name}!"
            llm_response = f"User name set to {clean_name}. Check conversation history for pending requests."

            await self._send_tool_call_event(context, "set_user_name", {"name": clean_name}, ui_response)
            
            # Return system status to LLM (do not speak directly)
            return llm_response

        except Exception as e:
            logger.error(f"[set_user_name] Error: {e}")
            response = "Sorry, I couldn't save that name. What should I call you?"
            await self._say_response(context, response)
            return None

    @function_tool
    async def add_user_preference(self, context: RunContext, preference: str) -> str:
        """Save a user preference mentioned during the conversation.

        Args:
            preference: The preference text to store
        """
        logger.debug(f"[add_user_preference] {preference}")

        try:
            clean_pref = preference.strip()
            if not clean_pref:
                response = "Sorry, I didn't catch that preference. Could you repeat it?"
                await self._say_response(context, response)
                return None

            if clean_pref not in self.context.user_preferences:
                self.context.user_preferences.append(clean_pref)
            
            # Track preference
            if clean_pref not in self.context.tracker.user_preferences:
                self.context.tracker.user_preferences.append(clean_pref)

            response = "Got it. Anything else?"
            await self._send_tool_call_event(context, "add_user_preference", {"preference": clean_pref}, response)
            await self._say_response(context, response)
            return None

        except Exception as e:
            logger.error(f"[add_user_preference] Error: {e}")
            response = "Sorry, I couldn't save that preference."
            await self._say_response(context, response)
            return None

    @function_tool
    async def fetch_slots(self, context: RunContext, date: str = None) -> str:
        """Fetch available appointment slots for a given date.
        
        Args:
            date: Date to check slots for (YYYY-MM-DD format). If not provided, shows next 7 days.
        """
        logger.debug(f"[fetch_slots] {date or 'tomorrow'}")
        
        try:
            normalized_date = self._normalize_date(date) if date else None
            tomorrow = self._tomorrow_date()
            allowed_slots = self._allowed_slots_for_date(tomorrow)
            booked_slots = await self.db.get_booked_slots(tomorrow)
            available_slots = [
                slot for slot in allowed_slots
                if f"{tomorrow} {slot['time']}" not in booked_slots
            ]

            if not available_slots:
                response = "Sorry, tomorrow is fully booked. I can only book for tomorrow."
            else:
                response = (
                    f"Tomorrow I have {self._format_slots(available_slots)}. Which time works for you?"
                )
            
            await self._send_tool_call_event(context, "fetch_slots", {"date": normalized_date or date}, response)
            
            return response
                    
        except Exception as e:
            logger.error(f"[fetch_slots] Error: {e}")
            response = "Can't check slots right now. Try again?"
            await self._say_response(context, response)
            return response

    @function_tool
    async def book_appointment(self, context: RunContext, date: str, time: str, purpose: str = "General consultation") -> str:
        """Book an appointment for the identified user.
        
        Args:
            date: Appointment date (YYYY-MM-DD format)
            time: Appointment time (HH:MM format)
            purpose: Purpose or reason for the appointment
        """
        logger.debug(f"[book_appointment] {date} {time}")
        
        if not self.context.user_id:
            logger.warning("[book_appointment] User not identified")
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
                logger.debug(f"[book_appointment] Slot {datetime_str} already booked")
                allowed_slots = self._allowed_slots_for_date(normalized_date)
                available_slots = [
                    slot for slot in allowed_slots
                    if f"{normalized_date} {slot['time']}" not in booked_slots
                ]

                if not available_slots:
                    response = (
                        "Sorry, tomorrow is fully booked. "
                        "Would you like to check another day?"
                    )
                else:
                    response = (
                        f"Sorry, {self._format_time_ampm(normalized_time)} is taken. "
                        f"I can do {self._format_slots(available_slots)}. Which time works?"
                    )
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
                'contact_number': self.context.user_phone,
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
            
            # Track appointment booking
            self.context.tracker.track_appointment_booked({
                'date': normalized_date,
                'time': self._format_time_ampm(normalized_time),
                'purpose': purpose
            })
            
            response = (
                f"Perfect! You're all set for tomorrow at {self._format_time_ampm(normalized_time)}. "
                "Anything else?"
            )
            
            await self._send_tool_call_event(context, "book_appointment", 
                {"date": normalized_date, "time": normalized_time, "purpose": purpose}, response)
            
            # Return context for LLM to confirm
            return response
            
        except Exception as e:
            logger.error(f"[book_appointment] Error: {e}")
            response = "Sorry, couldn't book that. Try a different time?"
            await self._say_response(context, response)
            return response

    @function_tool
    async def retrieve_appointments(self, context: RunContext) -> str:
        """Retrieve all appointments for the identified user.
        """
        logger.debug("[retrieve_appointments]")
        
        if not self.context.user_id:
            logger.warning("[retrieve_appointments] User not identified")
            response = "I need to identify you first. Could you please provide your phone number?"
            await self._say_response(context, response)
            return None
        
        try:
            appointments = await self.db.get_user_appointments(self.context.user_id)
            
            if not appointments:
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
            
            # Track appointments viewed
            self.context.tracker.track_appointment_viewed(upcoming)
            
            response_parts = []
            
            if upcoming:
                response_parts.append("Your upcoming appointments:")
                for apt in upcoming[:3]:  # Limit to 3 for brevity
                    formatted_date = apt['datetime'].strftime("%A, %B %d at %I:%M %p")
                    response_parts.append(f"{formatted_date} for {apt['purpose']}")
            
            response = " ".join(response_parts) + ". Need to change anything?"
            
            await self._send_tool_call_event(context, "retrieve_appointments", 
                {"count": len(appointments)}, response)
            
            # Return full response to LLM
            return response
            
        except Exception as e:
            logger.error(f"[retrieve_appointments] Error: {e}")
            response = "I'm having trouble accessing your appointments right now. Please try again in a moment."
            await self._say_response(context, response)
            return response

    @function_tool
    async def cancel_appointment(self, context: RunContext, appointment_id: str = None, date: str = None, time: str = None) -> str:
        """Cancel an appointment by ID or date/time.
        
        Args:
            appointment_id: The appointment ID to cancel
            date: Appointment date (YYYY-MM-DD format) 
            time: Appointment time (HH:MM format)
        """
        logger.debug(f"[cancel_appointment] {appointment_id or f'{date} {time}'}")
        
        if not self.context.user_id:
            logger.warning("[cancel_appointment] User not identified")
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
            
            # Track cancellation
            self.context.tracker.track_appointment_cancelled(str(appointment['_id']))
            
            formatted_date = appointment['datetime'].strftime("%A, %B %d at %I:%M %p")
            
            response = f"I've cancelled your appointment on {formatted_date}. Anything else?"

            await self._send_tool_call_event(context, "cancel_appointment", 
                {"date": date, "time": time}, response)
            
            # Return response for LLM to confirm
            return response
            
        except Exception as e:
            logger.error(f"[cancel_appointment] Error: {e}")
            response = "I'm sorry, I couldn't cancel that appointment right now. Please try again."
            await self._say_response(context, response)
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
        logger.debug(f"[modify_appointment] {appointment_id}")
        
        if not self.context.user_id:
            logger.warning("[modify_appointment] User not identified")
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
            
            # Track modification
            self.context.tracker.track_appointment_modified(
                str(appointment['_id']),
                {
                    'date': updates.get('date'),
                    'time': updates.get('time'),
                    'purpose': updates.get('purpose')
                }
            )
            
            if 'datetime' in updates:
                new_date_formatted = updates['datetime'].strftime("%A, %B %d at %I:%M %p")
                response = f"Updated! Your appointment is now {new_date_formatted}."
            else:
                response = f"Updated your appointment purpose to {updates['purpose']}."
            
            await self._send_tool_call_event(context, "modify_appointment", 
                {"appointment_id": appointment_id, "updates": updates}, response)

            # Return response for LLM
            return response
            
        except Exception as e:
            logger.error(f"[modify_appointment] Error: {e}")
            response = "I'm sorry, I couldn't modify that appointment right now. Please try again."
            await self._say_response(context, response)
            return response

    @function_tool
    async def end_conversation(self, context: RunContext) -> str:
        """End the conversation and generate a summary.
        """
        logger.debug("[end_conversation]")
        
        try:
            # Generate enhanced conversation summary using the tracker
            summary_data = SummaryGenerator.generate_summary(self.context.tracker)
            
            # Save summary to database
            if self.context.user_id:
                await self.db.save_conversation_summary(summary_data)
            else:
                logger.warning("[end_conversation] No user ID, skipping summary save")
            
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
            return None
            
        except Exception as e:
            logger.error(f"[end_conversation] Error: {e}")
            response = "Thank you for using our appointment booking service! Have a great day!"
            await self._say_response(context, response)
            return None
