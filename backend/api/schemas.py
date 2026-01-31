from typing import Optional
from pydantic import BaseModel

class TokenRequest(BaseModel):
    roomName: str
    participantName: str

class TokenResponse(BaseModel):
    token: str
    url: str

class UserCreate(BaseModel):
    phone: str
    name: str
    email: Optional[str] = None

class AppointmentCreate(BaseModel):
    user_phone: str
    date: str
    time: str
    purpose: str = "General consultation"

class AppointmentUpdate(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    purpose: Optional[str] = None
    status: Optional[str] = None
