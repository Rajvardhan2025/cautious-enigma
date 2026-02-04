from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class AppointmentStatus(Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


@dataclass
class User:
    phone: str
    name: str
    email: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phone": self.phone,
            "name": self.name,
            "email": self.email,
            "preferences": self.preferences or {},
            "created_at": self.created_at or datetime.utcnow(),
            "updated_at": self.updated_at or datetime.utcnow(),
        }


@dataclass
class Appointment:
    user_id: str
    date: str  # YYYY-MM-DD format
    time: str  # HH:MM format
    datetime: datetime
    purpose: str
    status: AppointmentStatus = AppointmentStatus.CONFIRMED
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "date": self.date,
            "time": self.time,
            "datetime": self.datetime,
            "purpose": self.purpose,
            "status": self.status.value,
            "notes": self.notes,
            "created_at": self.created_at or datetime.utcnow(),
            "updated_at": self.updated_at or datetime.utcnow(),
        }


@dataclass
class ConversationSummary:
    user_id: str
    user_phone: str
    conversation_id: str
    conversation_date: datetime
    appointments_discussed: List[Dict[str, Any]]
    user_preferences: List[str]
    summary_text: str
    duration_minutes: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "user_phone": self.user_phone,
            "conversation_id": self.conversation_id,
            "conversation_date": self.conversation_date,
            "appointments_discussed": self.appointments_discussed,
            "user_preferences": self.user_preferences,
            "summary_text": self.summary_text,
            "duration_minutes": self.duration_minutes,
        }


@dataclass
class ToolCallEvent:
    """Represents a tool call event for frontend display"""

    tool_name: str
    parameters: Dict[str, Any]
    result: str
    timestamp: datetime
    status: str = "success"  # success, error, pending

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
        }
