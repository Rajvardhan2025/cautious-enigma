from pydantic import BaseModel

# Only token schemas are used - agent handles all user/appointment operations through tools

class TokenRequest(BaseModel):
    roomName: str
    participantName: str

class TokenResponse(BaseModel):
    token: str
    url: str
