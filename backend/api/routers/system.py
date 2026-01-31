import os
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from livekit import api
from api.schemas import TokenRequest, TokenResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@router.post("/api/token", response_model=TokenResponse)
async def generate_token(request: TokenRequest):
    """Generate LiveKit access token for room connection"""
    try:
        # Get LiveKit configuration from environment
        livekit_url = os.getenv("LIVEKIT_URL")
        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
        
        if not all([livekit_url, livekit_api_key, livekit_api_secret]):
            raise HTTPException(
                status_code=500,
                detail="LiveKit configuration not found"
            )
        
        # Create room if it doesn't exist
        try:
            livekit_api = api.LiveKitAPI(
                url=livekit_url,
                api_key=livekit_api_key,
                api_secret=livekit_api_secret
            )
            
            await livekit_api.room.create_room(
                api.CreateRoomRequest(name=request.roomName)
            )
            logger.info(f"Created room: {request.roomName}")
        except Exception as e:
            # Room might already exist, that's okay
            logger.info(f"Room may already exist: {e}")
        
        # Create access token
        token = api.AccessToken(livekit_api_key, livekit_api_secret) \
            .with_identity(request.participantName) \
            .with_name(request.participantName) \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=request.roomName,
                can_publish=True,
                can_subscribe=True,
            )).to_jwt()
        
        logger.info(f"Generated token for {request.participantName} in room {request.roomName}")
        
        return TokenResponse(token=token, url=livekit_url)
        
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))
