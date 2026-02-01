import logging
import os
import json
from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    room_io,
)
from livekit.plugins import noise_cancellation, silero, deepgram, google, openai, bey
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from agent.tools import VoiceAppointmentAgent

# Configure logging - only show important messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

# Silence noisy loggers
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pymongo.connection").setLevel(logging.WARNING)
logging.getLogger("pymongo.command").setLevel(logging.WARNING)
logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
logging.getLogger("pymongo.serverSelection").setLevel(logging.WARNING)
logging.getLogger("livekit.plugins.turn_detector").setLevel(logging.WARNING)
logging.getLogger("livekit.plugins.silero").setLevel(logging.WARNING)

logger = logging.getLogger("agent")


load_dotenv(".env.local")


livekit_url = os.getenv("LIVEKIT_URL")
logger.info(f"🔌 LIVEKIT_URL loaded: {livekit_url}")



def get_llm_instance():
    """Get LLM instance based on environment configuration."""
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    logger.info(f"Initializing LLM provider: {provider}")
    
    if provider == "cerebras":
        model = os.getenv("CEREBRAS_MODEL", "llama3.1-8b")
        temperature = float(os.getenv("CEREBRAS_TEMPERATURE", "0.4"))
        parallel_tool_calls = os.getenv("CEREBRAS_PARALLEL_TOOL_CALLS", "true").lower() == "true"
        tool_choice = os.getenv("CEREBRAS_TOOL_CHOICE", "auto")
        logger.info(f"Using Cerebras with model: {model}")
        return openai.LLM.with_cerebras(
            model=model,
            temperature=temperature,
            parallel_tool_calls=parallel_tool_calls,
            tool_choice=tool_choice,
        )
    
    elif provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        logger.info(f"Using OpenAI with model: {model}")
        return openai.LLM(model=model)
    
    elif provider == "gemini":
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
        logger.info(f"Using Gemini with model: {model}")
        return google.LLM(model=model)
    
    else:
        logger.warning(f"Unknown LLM provider '{provider}', defaulting to Gemini")
        return google.LLM(model="gemini-2.0-flash-lite")


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="voice-appointment-agent")
async def voice_appointment_agent(ctx: JobContext):
    try:
        # Join the room and connect to the user
        logger.info(f"🎯 Agent received job request for room: {ctx.room.name}")
        
        await ctx.connect()
        
        logger.info(f"✅ Agent connected to room: {ctx.room.name}")

        # Logging setup
        ctx.log_context_fields = {
            "room": ctx.room.name,
        }
        
        @ctx.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(f"👤 Participant joined: {participant.identity}")
        
        @ctx.room.on("participant_disconnected")
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            logger.info(f"� Participant disconnected: {participant.identity}")

        # Set up voice AI pipeline with Deepgram and configurable LLM
        logger.info("🔧 Initializing agent session with STT, LLM, and TTS")
        
        session = AgentSession(
            # Use Deepgram for STT
            stt=deepgram.STTv2(
                model="flux-general-en",
                eager_eot_threshold=0.4,
                keyterms=[
                    "appointment",
                    "book",
                    "booking",
                    "reschedule",
                    "cancel",
                    "phone number",
                    "tomorrow",
                    "12 PM",
                    "3 PM",
                    "5 PM",
                    "6 PM",
                    "7 PM",
                ],
            ),
            # Use configured LLM (Gemini, Cerebras, or OpenAI)
            llm=get_llm_instance(),
            # Use Deepgram for TTS  
            tts=deepgram.TTS(
                model="aura-2-asteria-en",
            ),
            # VAD and turn detection
            turn_detection="stt",
            vad=silero.VAD.load(),
        )
        
        logger.info("✅ Agent session initialized successfully")

        # Start the session with our appointment agent
        logger.info("🤖 Creating VoiceAppointmentAgent instance")
        agent = VoiceAppointmentAgent()
        
        # Add event listeners for session events
        @session.on("user_speech_committed")
        def on_user_speech(msg):
            logger.info(f"user: {msg.text}")
            agent.context.last_user_message = msg.text
        
        @session.on("agent_speech_committed")
        def on_agent_speech(msg):
            logger.info(f"agent: {msg.text}")
            agent.context.last_agent_message = msg.text
        
        @session.on("agent_speech_interrupted")
        def on_agent_interrupted(msg):
            logger.warning(f"⚠️  Interrupted: {msg.text[:50]}...")
        
        @session.on("function_calls_collected")
        def on_function_calls(calls):
            for call in calls:
                logger.info(f"🔧 Calling tool: {call.function_info.name}")
        
        @session.on("function_calls_finished")
        def on_function_finished(calls):
            for call in calls:
                if call.exception:
                    logger.error(f"❌ Tool failed: {call.function_info.name} - {call.exception}")
                else:
                    logger.info(f"✅ Tool completed: {call.function_info.name}")
        
        logger.info("🚀 Starting agent session")
        
        # Extract user context from job metadata if available
        user_context = None
        if ctx.room.metadata:
            try:
                metadata = json.loads(ctx.room.metadata)
                user_context = metadata.get("user_context")
                use_avatar = metadata.get("use_avatar", False)
                if user_context:
                    logger.info(f"📋 Loaded user context from metadata: {user_context.get('name', 'Unknown')}")
            except Exception as e:
                logger.warning(f"Failed to parse room metadata: {e}")
                use_avatar = False
        else:
            use_avatar = False
        
        # Create agent with optional user context
        logger.info("🤖 Creating VoiceAppointmentAgent instance")
        agent = VoiceAppointmentAgent(user_context=user_context)
        
        # Start Beyond Presence avatar if configured
        bey_api_key = os.getenv("BEY_API_KEY")
        avatar_id = os.getenv("BEY_AVATAR_ID")
        
        if bey_api_key and avatar_id and use_avatar:
            logger.info("🧑‍🎤 Starting Beyond Presence avatar")
            try:
                # Ensure LiveKit URL is in WebSocket format (wss://)
                livekit_ws_url = livekit_url
                if livekit_url and livekit_url.startswith("https://"):
                    livekit_ws_url = livekit_url.replace("https://", "wss://")
                    logger.info(f"🔄 Converted HTTPS to WSS: {livekit_ws_url}")
                elif livekit_url and livekit_url.startswith("http://"):
                    livekit_ws_url = livekit_url.replace("http://", "ws://")
                    logger.info(f"🔄 Converted HTTP to WS: {livekit_ws_url}")
                
                avatar = bey.AvatarSession(avatar_id=avatar_id)
                await avatar.start(
                    session, 
                    room=ctx.room,
                    livekit_url=livekit_ws_url
                )
                logger.info("✅ Beyond Presence avatar started")
            except Exception as e:
                logger.error(f"❌ Failed to start BEY avatar: {e}")
        elif not use_avatar:
            logger.info("⏭️  Avatar disabled by user")
        
        await session.start(
            agent=agent,
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                    if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC(),
                ),
                # Enable text output to send transcriptions to frontend
                text_output=True,
            ),
        )
        
        logger.info("✅ Agent session started successfully")
        
        # Send initial greeting with better introduction flow
        logger.info("👋 Sending initial greeting to user")
        await session.say(
            "Hi there! I'm Alya, your appointment scheduling assistant. I'm here to help you book, reschedule, or manage your appointments. What can I help you with today?",
            allow_interruptions=True,
        )
        
        logger.info("🎧 Agent is now listening for user input")
        
    except Exception as e:
        logger.error(f"❌ Fatal error in agent session: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    cli.run_app(server)