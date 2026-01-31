from pydantic import BaseModel
from typing import Optional

class SessionRequest(BaseModel):
    """Request to create a new session - backend generates everything"""
    participantName: Optional[str] = None  # Optional, backend can generate

class SessionResponse(BaseModel):
    """Complete session info for frontend to join"""
    token: str
    url: str
    roomName: str
    participantName: str
