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

from agent.tools import VoiceAppointmentAgent

# Configure logging - only show important messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
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


def get_llm_instance():
    """Get LLM instance based on environment configuration."""
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "cerebras":
        model = os.getenv("CEREBRAS_MODEL", "llama3.1-8b")
        temperature = float(os.getenv("CEREBRAS_TEMPERATURE", "0.4"))
        parallel_tool_calls = (
            os.getenv("CEREBRAS_PARALLEL_TOOL_CALLS", "true").lower() == "true"
        )
        tool_choice = os.getenv("CEREBRAS_TOOL_CHOICE", "auto")
        logger.info(f"[LLM] Using Cerebras: {model}")
        return openai.LLM.with_cerebras(
            model=model,
            temperature=temperature,
            parallel_tool_calls=parallel_tool_calls,
            tool_choice=tool_choice,
        )

    elif provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        logger.info(f"[LLM] Using OpenAI: {model}")
        return openai.LLM(model=model)

    elif provider == "gemini":
        model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
        logger.info(f"[LLM] Using Gemini: {model}")
        return google.LLM(model=model)

    else:
        logger.warning(f"[LLM] Unknown provider '{provider}', defaulting to Gemini")
        return google.LLM(model="gemini-2.0-flash-lite")


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="voice-appointment-agent")
async def voice_appointment_agent(ctx: JobContext):
    try:
        logger.info(f"[Session] Connecting to room: {ctx.room.name}")
        await ctx.connect()

        # Logging setup
        ctx.log_context_fields = {
            "room": ctx.room.name,
        }

        @ctx.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(f"[Room] Participant joined: {participant.identity}")

        @ctx.room.on("participant_disconnected")
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            logger.info(f"[Room] Participant left: {participant.identity}")

        # Set up voice AI pipeline with Deepgram and configurable LLM
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

        # Add event listeners for session events
        @session.on("user_speech_committed")
        def on_user_speech(msg):
            logger.debug(f"[User] {msg.text}")

        @session.on("agent_speech_committed")
        def on_agent_speech(msg):
            logger.debug(f"[Agent] {msg.text}")

        @session.on("agent_speech_interrupted")
        def on_agent_interrupted(msg):
            logger.debug(f"[Agent] Interrupted")

        @session.on("function_calls_finished")
        def on_function_finished(calls):
            for call in calls:
                if call.exception:
                    logger.error(
                        f"[Tool] {call.function_info.name} failed: {call.exception}"
                    )

        # Extract user context from job metadata if available
        user_context = None
        use_avatar = False
        bey_api_key = os.getenv("BEY_API_KEY")
        avatar_id = os.getenv("BEY_AVATAR_ID")
        logger.info(f"[Avatar] Avatar ID: {avatar_id}")

        if ctx.room.metadata:
            try:
                metadata = json.loads(ctx.room.metadata)
                user_context = metadata.get("user_context")
                use_avatar = metadata.get("use_avatar", False)
            except Exception as e:
                logger.warning(f"[Metadata] Failed to parse: {e}")

        # Create agent with optional user context
        agent = VoiceAppointmentAgent(user_context=user_context)

        # Store agent reference for event handlers
        @session.on("user_speech_committed")
        def on_user_speech_update(msg):
            agent.context.last_user_message = msg.text

        @session.on("agent_speech_committed")
        def on_agent_speech_update(msg):
            agent.context.last_agent_message = msg.text

        await session.start(
            agent=agent,
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                    if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC(),
                ),
                text_output=True,
            ),
        )
        
        logger.info("[Session] Started successfully")

        # Start Beyond Presence avatar after session starts
        if bey_api_key and avatar_id and use_avatar:
            try:
                # Convert HTTP(S) URL to WebSocket format for BEY
                bey_url = livekit_url
                if bey_url:
                    if bey_url.startswith("https://"):
                        bey_url = bey_url.replace("https://", "wss://")
                    elif bey_url.startswith("http://"):
                        bey_url = bey_url.replace("http://", "ws://")

                avatar = bey.AvatarSession(avatar_id=avatar_id)
                await avatar.start(session, room=ctx.room, livekit_url=bey_url)
                logger.info("[Avatar] Started")
            except Exception as e:
                logger.error(f"[Avatar] Failed to start: {e}")

        # Send initial greeting
        await session.say(
            "Hi there! I'm Alya, your appointment scheduling assistant. I'm here to help you book, reschedule, or manage your appointments. What can I help you with today?",
            allow_interruptions=True,
        )
        
    except Exception as e:
        logger.error(f"[Session] Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    cli.run_app(server)