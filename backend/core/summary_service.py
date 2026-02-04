"""
Captures rich context throughout the conversation and generates natural summaries.
"""

import logging
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    import google.genai as genai
except ImportError:
    genai = None

logger = logging.getLogger("summary_service")


@dataclass
class ConversationEvent:
    """Represents a significant event in the conversation"""

    timestamp: datetime
    event_type: (
        str  # 'user_identified', 'appointment_booked', 'appointment_viewed', etc.
    )
    details: Dict[str, Any]


@dataclass
class ConversationTracker:
    """Tracks conversation context for enhanced summary generation"""

    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    user_phone: Optional[str] = None
    user_name: Optional[str] = None
    user_preferences: List[str] = field(default_factory=list)

    # Track conversation events
    events: List[ConversationEvent] = field(default_factory=list)

    # Track appointments discussed
    appointments_booked: List[Dict] = field(default_factory=list)
    appointments_viewed: List[Dict] = field(default_factory=list)
    appointments_modified: List[Dict] = field(default_factory=list)
    appointments_cancelled: List[Dict] = field(default_factory=list)

    # Track user interactions
    questions_asked: List[str] = field(default_factory=list)
    concerns_raised: List[str] = field(default_factory=list)

    # Conversation metadata
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None

    def add_event(self, event_type: str, details: Dict[str, Any]):
        """Add a conversation event"""
        event = ConversationEvent(
            timestamp=datetime.utcnow(), event_type=event_type, details=details
        )
        self.events.append(event)
        logger.debug(f"Added event: {event_type}")

    def track_appointment_booked(self, appointment: Dict):
        """Track when an appointment is booked"""
        self.appointments_booked.append(appointment)
        self.add_event("appointment_booked", appointment)

    def track_appointment_viewed(self, appointments: List[Dict]):
        """Track when appointments are viewed"""
        self.appointments_viewed.extend(appointments)
        self.add_event("appointments_viewed", {"count": len(appointments)})

    def track_appointment_modified(self, appointment_id: str, changes: Dict):
        """Track when an appointment is modified"""
        modification = {
            "appointment_id": appointment_id,
            "changes": changes,
            "timestamp": datetime.utcnow(),
        }
        self.appointments_modified.append(modification)
        self.add_event("appointment_modified", modification)

    def track_appointment_cancelled(self, appointment_id: str):
        """Track when an appointment is cancelled"""
        cancellation = {
            "appointment_id": appointment_id,
            "timestamp": datetime.utcnow(),
        }
        self.appointments_cancelled.append(cancellation)
        self.add_event("appointment_cancelled", cancellation)

    def track_user_question(self, question: str):
        """Track questions the user asked"""
        self.questions_asked.append(question)

    def track_concern(self, concern: str):
        """Track concerns or issues raised"""
        self.concerns_raised.append(concern)

    def get_duration_minutes(self) -> int:
        """Calculate conversation duration in minutes"""
        end = self.end_time or datetime.utcnow()
        duration = (end - self.start_time).total_seconds() / 60
        return int(duration)


class SummaryGenerator:
    """Generates natural, comprehensive conversation summaries"""

    _client = None

    @classmethod
    def get_genai_client(cls):
        """Get or create a Gemini client for text summarization"""
        if cls._client is None:
            if genai is None:
                logger.warning(
                    "google-genai package not available. Text summarization disabled."
                )
                return None

            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.warning("GOOGLE_API_KEY not set. Text summarization disabled.")
                return None

            logger.info("Initializing Google Generative AI client for summarization")
            cls._client = genai.Client(api_key=api_key)

        return cls._client

    @staticmethod
    async def generate_text_summary_from_messages(
        messages: List[Dict[str, str]],
    ) -> str:
        """
        Generate a concise text summary from conversation messages using Gemini 2.0 Flash Lite.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
                     Format: [{"role": "user|assistant", "content": "..."}, ...]

        Returns:
            A concise summary of the conversation
        """
        client = SummaryGenerator.get_genai_client()

        if client is None:
            logger.warning("Gemini client not available. Returning template summary.")
            return "Appointment consultation completed."

        try:
            # Format messages for the summarization prompt
            formatted_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                formatted_messages.append(f"{role.upper()}: {content}")

            messages_text = "\n".join(formatted_messages)

            # Create a summarization prompt
            prompt = f"""Analyze this appointment agent conversation and provide a concise summary covering:
1. What appointment(s) were booked, rescheduled, or cancelled
2. Any key dates/times mentioned
3. User preferences or special notes
4. Overall outcome of the conversation

Keep the summary to at max 2-3 sentences, focused on actionable information.

CONVERSATION:
{messages_text}

SUMMARY:"""

            # Use Gemini 2.0 Flash Lite to generate the summary
            logger.info("Generating text summary with Gemini 2.0 Flash Lite...")
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite", contents=prompt
            )

            summary_text = (
                response.text.strip()
                if response.text
                else "Appointment consultation completed."
            )
            logger.info(
                f"Summary generated successfully: {len(summary_text)} characters"
            )

            return summary_text

        except Exception as e:
            logger.error(f"Error generating text summary with Gemini: {e}")
            return "Appointment consultation completed."

    @staticmethod
    async def generate_frontend_summary(
        tracker: ConversationTracker,
        messages: Optional[List[Dict[str, str]]] = None,
        ai_timeout: float = 6.0,
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive summary ready for frontend consumption.
        Returns static summary by default. If AI summary completes, includes it as ai_summary.

        Args:
            tracker: ConversationTracker with conversation context
            messages: Optional list of messages for AI text summarization
            ai_timeout: Timeout in seconds for AI summary generation (default 6s)

        Returns:
            Dictionary with frontend-ready summary data including ai_summary if available
        """
        tracker.end_time = datetime.utcnow()

        # Start with the static summary template
        summary_data = SummaryGenerator.generate_summary(tracker)

        # Try to get AI summary if messages provided
        if messages:
            try:
                logger.info(
                    f"Attempting AI summary generation with {ai_timeout}s timeout..."
                )
                ai_summary_task = asyncio.create_task(
                    SummaryGenerator.generate_text_summary_from_messages(messages)
                )
                try:
                    ai_summary_text = await asyncio.wait_for(
                        ai_summary_task, timeout=ai_timeout
                    )
                    summary_data["summary_text"] = ai_summary_text
                    logger.info(f"AI summary generated: {ai_summary_text[:100]}...")
                except asyncio.TimeoutError:
                    logger.warning(
                        f"AI summary generation timed out after {ai_timeout}s"
                    )
                    ai_summary_task.cancel()
            except Exception as e:
                logger.warning(f"Could not generate AI summary: {e}")

        return summary_data

    @staticmethod
    def generate_summary(
        tracker: ConversationTracker, messages: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive summary from conversation tracker.

        Args:
            tracker: ConversationTracker with conversation context
            messages: Optional list of messages for Gemini text summarization

        Returns:
            Dictionary with summary data including AI-generated text summary
        """
        tracker.end_time = datetime.utcnow()

        summary_text = SummaryGenerator._generate_summary_text(tracker)

        if messages:
            logger.info(
                "Messages provided for potential Gemini summarization (async operation)"
            )

        # Compile all appointments discussed
        all_appointments = []

        # Add booked appointments
        for apt in tracker.appointments_booked:
            all_appointments.append(
                {
                    "date": apt.get("date", ""),
                    "time": apt.get("time", ""),
                    "purpose": apt.get("purpose", "General appointment"),
                    "status": "Booked",
                }
            )

        # Add modified appointments
        for mod in tracker.appointments_modified:
            changes = mod.get("changes", {})
            all_appointments.append(
                {
                    "date": changes.get("date", "Modified"),
                    "time": changes.get("time", ""),
                    "purpose": changes.get("purpose", "Modified appointment"),
                    "status": "Rescheduled",
                }
            )

        # Add cancelled appointments
        for cancel in tracker.appointments_cancelled:
            all_appointments.append(
                {
                    "date": "Cancelled",
                    "time": "",
                    "purpose": "Cancelled appointment",
                    "status": "Cancelled",
                }
            )

        return {
            "conversation_id": tracker.conversation_id,
            "user_id": tracker.user_id,
            "user_phone": tracker.user_phone,
            "user_name": tracker.user_name,
            "conversation_date": tracker.start_time,
            "duration_minutes": tracker.get_duration_minutes(),
            "appointments_discussed": all_appointments,
            "user_preferences": tracker.user_preferences,
            "summary_text": summary_text,
            "events_count": len(tracker.events),
        }

    @staticmethod
    def _generate_summary_text(tracker: ConversationTracker) -> str:
        """Generate natural summary text from conversation context"""
        parts = []

        # Opening - who we spoke with
        if tracker.user_name and tracker.user_name != "User":
            parts.append(f"Spoke with {tracker.user_name}")
        else:
            parts.append("Completed appointment conversation")

        # What happened - appointments
        if tracker.appointments_booked:
            for apt in tracker.appointments_booked:
                purpose = apt.get("purpose", "appointment")
                date = apt.get("date", "tomorrow")
                time = apt.get("time", "")
                parts.append(f"Successfully booked a {purpose} for {date} at {time}")

        if tracker.appointments_modified:
            count = len(tracker.appointments_modified)
            if count == 1:
                parts.append("Rescheduled an existing appointment")
            else:
                parts.append(f"Rescheduled {count} appointments")

        if tracker.appointments_cancelled:
            count = len(tracker.appointments_cancelled)
            if count == 1:
                parts.append("Cancelled an appointment")
            else:
                parts.append(f"Cancelled {count} appointments")

        if tracker.appointments_viewed and not (
            tracker.appointments_booked
            or tracker.appointments_modified
            or tracker.appointments_cancelled
        ):
            count = len(tracker.appointments_viewed)
            if count == 1:
                parts.append("Reviewed their upcoming appointment")
            else:
                parts.append(f"Reviewed {count} upcoming appointments")

        # User preferences
        if tracker.user_preferences:
            pref_text = ", ".join(tracker.user_preferences)
            parts.append(f"Noted preferences: {pref_text}")

        # Questions or concerns
        if tracker.concerns_raised:
            parts.append(f"Addressed {len(tracker.concerns_raised)} concern(s)")

        # If nothing significant happened
        if len(parts) <= 1:
            parts.append("Discussed appointment options and availability")

        # Join with proper punctuation
        return ". ".join(parts) + "."
