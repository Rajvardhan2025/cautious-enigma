import os
import logging
import time
import random
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Header
from livekit import api
from api.schemas import SessionRequest, SessionResponse

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_livekit_credentials():
    livekit_url = os.getenv("LIVEKIT_URL")
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    if not all([livekit_url, livekit_api_key, livekit_api_secret]):
        raise HTTPException(status_code=500, detail="LiveKit configuration not found")
    return livekit_url, livekit_api_key, livekit_api_secret

def generate_room_name() -> str:
    """Generate unique room name"""
    timestamp = int(time.time() * 1000)
    random_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
    return f"voice-agent-{timestamp}-{random_id}"

def generate_participant_name() -> str:
    """Generate unique participant name"""
    random_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
    return f"user-{random_id}"

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@router.post("/api/session", response_model=SessionResponse)
async def create_session(request: SessionRequest):
    """Create a new session - backend handles room creation, agent dispatch, and token generation"""
    try:
        # Get LiveKit configuration from environment
        livekit_url, livekit_api_key, livekit_api_secret = _get_livekit_credentials()
        
        # Generate room and participant names
        room_name = generate_room_name()
        participant_name = request.participantName or generate_participant_name()
        use_avatar = True if request.useAvatar is None else bool(request.useAvatar)
        
        logger.info(f"Creating session - Room: {room_name}, Participant: {participant_name}")
        
        # Initialize LiveKit API client
        livekit_api = api.LiveKitAPI(
            url=livekit_url,
            api_key=livekit_api_key,
            api_secret=livekit_api_secret
        )
        
        # Create room
        try:
            await livekit_api.room.create_room(
                api.CreateRoomRequest(
                    name=room_name,
                    empty_timeout=30,  # Close room 30 seconds after last participant leaves
                    departure_timeout=20,  # Close room 20 seconds after user leaves
                    max_participants=10,
                    metadata=json.dumps({"use_avatar": use_avatar}),
                )
            )
            logger.info(f"Created room: {room_name}")
        except Exception as e:
            logger.error(f"Failed to create room: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create room: {str(e)}")
        
        # Dispatch agent to the room
        try:
            await livekit_api.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name="voice-appointment-agent",
                    room=room_name,
                )
            )
            logger.info(f"Dispatched agent to room: {room_name}")
        except Exception as e:
            logger.error(f"Failed to dispatch agent: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to dispatch agent: {str(e)}")
        
        # Generate access token for participant
        token = api.AccessToken(livekit_api_key, livekit_api_secret) \
            .with_identity(participant_name) \
            .with_name(participant_name) \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )).to_jwt()
        
        logger.info(f"Generated token for {participant_name} in room {room_name}")
        
        await livekit_api.aclose()
        
        return SessionResponse(
            token=token,
            url=livekit_url,
            roomName=room_name,
            participantName=participant_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/webhook/livekit")
async def livekit_webhook(
    request: Request,
    authorization: str | None = Header(default=None),
):
    """Receive LiveKit webhooks for lifecycle events."""
    body = (await request.body()).decode("utf-8")
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    try:
        _, livekit_api_key, livekit_api_secret = _get_livekit_credentials()
        receiver = api.WebhookReceiver(api.TokenVerifier(livekit_api_key, livekit_api_secret))
        token = authorization.replace("Bearer ", "")
        event = receiver.receive(body, token)
    except Exception as e:
        logger.error(f"Webhook verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid webhook")

    # Basic lifecycle handling
    event_type = event.event
    room_name = event.room.name if event.room else None
    identity = event.participant.identity if event.participant else None
    logger.info(f"LiveKit webhook: {event_type} room={room_name} identity={identity}")

    # If the user leaves, aggressively delete the room to terminate avatar sessions
    if event_type == "participant_left" and identity and not identity.startswith("agent"):
        try:
            livekit_url, livekit_api_key, livekit_api_secret = _get_livekit_credentials()
            livekit_api = api.LiveKitAPI(
                url=livekit_url,
                api_key=livekit_api_key,
                api_secret=livekit_api_secret,
            )
            if room_name:
                await livekit_api.room.delete_room(api.DeleteRoomRequest(room=room_name))
                logger.info(f"Room deleted from webhook: {room_name}")
            await livekit_api.aclose()
        except Exception as e:
            logger.error(f"Webhook room delete failed: {e}")

    return {"ok": True}
