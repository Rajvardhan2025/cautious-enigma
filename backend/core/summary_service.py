"""
Captures rich context throughout the conversation and generates natural summaries.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

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

    @staticmethod
    def generate_summary(tracker: ConversationTracker) -> Dict[str, Any]:
        """Generate a comprehensive summary from conversation tracker"""
        tracker.end_time = datetime.utcnow()

        # Generate natural summary text
        summary_text = SummaryGenerator._generate_summary_text(tracker)

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
