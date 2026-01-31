import logging
import os
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
from livekit.plugins import noise_cancellation, silero, deepgram, google, openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from agent.tools import VoiceAppointmentAgent

logger = logging.getLogger("agent")
logging.basicConfig(level=logging.INFO)

load_dotenv(".env.local")


def get_llm_instance():
    """Get LLM instance based on environment configuration."""
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    logger.info(f"Initializing LLM provider: {provider}")
    
    if provider == "cerebras":
        model = os.getenv("CEREBRAS_MODEL", "llama3.1-8b")
        logger.info(f"Using Cerebras with model: {model}")
        return openai.LLM.with_cerebras(model=model)
    
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
    # Join the room and connect to the user
    await ctx.connect()
    
    logger.info(f"Agent joining room: {ctx.room.name}")

    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    
    # Track if user has left
    user_left = False
    
    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        nonlocal user_left
        logger.info(f"Participant disconnected: {participant.identity}")
        # If a human participant leaves, mark for cleanup
        if not participant.identity.startswith("agent"):
            user_left = True

    # Set up voice AI pipeline with Deepgram and configurable LLM
    session = AgentSession(
        # Use Deepgram for STT
        stt=deepgram.STT(
            model="nova-3",
            language="en",
            smart_format=True,
            interim_results=True,
            endpointing_ms=400,  # Increased from 10ms to reduce false triggers
        ),
        # Use configured LLM (Gemini, Cerebras, or OpenAI)
        llm=get_llm_instance(),
        # Use Deepgram for TTS  
        tts=deepgram.TTS(
            model="aura-2-asteria-en",
        ),
        # VAD and turn detection
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=False,  # Disable to prevent speaking before user finishes
    )

    # Start the session with our appointment agent
    agent = VoiceAppointmentAgent()
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
    
    # Send initial greeting
    await session.say(
        "Hi! I'm your appointment assistant. What's your phone number?",
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(server)