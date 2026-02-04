import { useState, useEffect, useRef } from 'react';
import {
  useRoomContext,
  useTracks,
  ControlBar,
  VideoTrack
} from '@livekit/components-react';
import {
  RoomEvent,
  Track,
  Participant
} from 'livekit-client';
import { toast } from 'sonner';

import { AgentAudioVisualizerAura } from '@/components/agents-ui/agent-audio-visualizer-aura';
import LiveTranscript from './LiveTranscript';
import ToolCallDisplay from './ToolCallDisplay';
import { ToolCall, ConversationSummaryData } from '../types';
import { APP_CONSTANTS } from '../config/constants';

interface VoiceAgentInterfaceProps {
  onToolCall: (toolCall: Omit<ToolCall, 'id' | 'timestamp'>) => void;
  onConversationEnd: (summary: ConversationSummaryData) => void;
  onEndCall: () => void;
  toolCalls: ToolCall[];
  initialUseAvatar: boolean;
}

function VoiceAgentInterface({ onToolCall, onConversationEnd, onEndCall, toolCalls, initialUseAvatar }: VoiceAgentInterfaceProps) {
  const room = useRoomContext();
  const audioTracks = useTracks([Track.Source.Microphone]);
  const videoTracks = useTracks([Track.Source.Camera]);

  const [isAgentConnected, setIsAgentConnected] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [useAvatar, setUseAvatar] = useState(initialUseAvatar);
  const [isAvatarInitializing, setIsAvatarInitializing] = useState(false);
  const connectingToastRef = useRef<string | number | null>(null);

  // Get agent state for the visualizer
  const getAgentState = () => {
    if (!isAgentConnected) return 'connecting';
    if (isSpeaking) return 'speaking';
    if (isListening) return 'listening';
    return 'idle';
  };

  // Get the agent's audio track for visualization
  const agentAudioTrack = audioTracks.find(track => !track.participant.isLocal);

  // Show toast when connecting
  useEffect(() => {
    if (!isAgentConnected && !isAvatarInitializing && connectingToastRef.current === null) {
      connectingToastRef.current = toast.loading('Connecting to agent...', {
        duration: Infinity,
      });
    } else if (isAgentConnected && connectingToastRef.current !== null) {
      toast.success('Agent connected!', {
        id: connectingToastRef.current,
        duration: 2000
      });
      connectingToastRef.current = null;
    } else if (isAvatarInitializing && connectingToastRef.current !== null) {
      // Dismiss connecting toast when avatar starts initializing
      toast.dismiss(connectingToastRef.current);
      connectingToastRef.current = null;
    }
  }, [isAgentConnected, isAvatarInitializing]);

  useEffect(() => {
    if (!room) return;

    const checkForAgent = () => {
      const participants = Array.from(room.remoteParticipants.values());

      if (useAvatar) {
        // Avatar mode: Need exactly 2 agents - voice agent AND bey-agent
        const voiceAgent = participants.find(p => {
          const identity = p.identity.toLowerCase();
          return (identity.includes('voice') || identity.includes('agent')) && !identity.includes('bey');
        });
        const beyAgent = participants.find(p => {
          const identity = p.identity.toLowerCase();
          return identity.includes('bey');
        });

        // Check if bey agent has video track that is subscribed and has actual track
        const beyHasVideo = beyAgent && Array.from(beyAgent.trackPublications.values()).some(
          pub => pub.kind === Track.Kind.Video && pub.track && pub.isSubscribed
        );

        if (voiceAgent && beyAgent && beyHasVideo) {
          setIsAgentConnected(true);
          setIsAvatarInitializing(false);
        } else if (voiceAgent && beyAgent && !beyHasVideo) {
          // Both agents present but video not ready yet
          setIsAvatarInitializing(true);
          setIsAgentConnected(false);
        } else if (voiceAgent && !beyAgent) {
          // Voice agent present, waiting for avatar
          setIsAvatarInitializing(true);
          setIsAgentConnected(false);
        } else {
          setIsAgentConnected(false);
          setIsAvatarInitializing(false);
        }
      } else {
        // Non-avatar mode: Need exactly 1 agent (voice agent only)
        const voiceAgent = participants.find(p => {
          const identity = p.identity.toLowerCase();
          const hasAgentKeyword = APP_CONSTANTS.AGENT_IDENTITY_KEYWORDS.some(keyword =>
            identity.includes(keyword)
          );
          // Exclude bey-agent from non-avatar mode
          return hasAgentKeyword && !identity.includes('bey');
        });

        if (voiceAgent) {
          setIsAgentConnected(true);
        } else {
          setIsAgentConnected(false);
        }
      }
    };

    checkForAgent();

    const handleParticipantConnected = (participant: Participant) => {
      // Re-check agent status whenever a participant connects
      checkForAgent();
    };

    const handleParticipantDisconnected = (participant: Participant) => {
      // Re-check agent status when someone disconnects
      checkForAgent();
    };

    const handleTrackPublished = () => {
      // Re-check when any track is published (especially video for avatar)
      checkForAgent();
    };

    const handleTrackUnpublished = () => {
      // Re-check when tracks are unpublished
      checkForAgent();
    };

    const handleTrackSubscribed = () => {
      // Re-check when tracks are subscribed (this is when video is actually ready)
      checkForAgent();
    };

    const handleDataReceived = (payload: Uint8Array) => {
      try {
        const data = JSON.parse(new TextDecoder().decode(payload));

        if (data.type === 'tool_call') {
          onToolCall(data);
        } else if (data.type === 'conversation_summary') {
          onConversationEnd(data.summary);
        } else if (data.type === 'end_call') {
          onEndCall();
          if (room) {
            room.disconnect();
          }
        }
      } catch (error) {
        // Silently ignore parse errors
      }
    };

    room.on(RoomEvent.ParticipantConnected, handleParticipantConnected);
    room.on(RoomEvent.ParticipantDisconnected, handleParticipantDisconnected);
    room.on(RoomEvent.TrackPublished, handleTrackPublished);
    room.on(RoomEvent.TrackUnpublished, handleTrackUnpublished);
    room.on(RoomEvent.TrackSubscribed, handleTrackSubscribed);
    room.on(RoomEvent.DataReceived, handleDataReceived);

    return () => {
      room.off(RoomEvent.ParticipantConnected, handleParticipantConnected);
      room.off(RoomEvent.ParticipantDisconnected, handleParticipantDisconnected);
      room.off(RoomEvent.TrackPublished, handleTrackPublished);
      room.off(RoomEvent.TrackUnpublished, handleTrackUnpublished);
      room.off(RoomEvent.TrackSubscribed, handleTrackSubscribed);
      room.off(RoomEvent.DataReceived, handleDataReceived);
    };
  }, [room, onToolCall, onConversationEnd, onEndCall, useAvatar]);

  useEffect(() => {
    audioTracks.forEach(track => {
      if (track.participant.isLocal) {
        setIsListening(track.publication?.track?.isMuted === false);
      } else {
        setIsSpeaking(track.publication?.track?.isMuted === false);
      }
    });

    // Also re-check agent connection when audio tracks change
    // This catches cases where the agent was already in the room
    if (room && audioTracks.length > 0) {
      const participants = Array.from(room.remoteParticipants.values());
      if (participants.length > 0 && !isAgentConnected) {
        const checkForAgent = () => {
          if (useAvatar) {
            const voiceAgent = participants.find(p => {
              const identity = p.identity.toLowerCase();
              return (identity.includes('voice') || identity.includes('agent')) && !identity.includes('bey');
            });
            const beyAgent = participants.find(p => {
              const identity = p.identity.toLowerCase();
              return identity.includes('bey');
            });

            if (voiceAgent && beyAgent) {
              setIsAgentConnected(true);
            }
          } else {
            const voiceAgent = participants.find(p => {
              const identity = p.identity.toLowerCase();
              const hasAgentKeyword = APP_CONSTANTS.AGENT_IDENTITY_KEYWORDS.some(keyword =>
                identity.includes(keyword)
              );
              return hasAgentKeyword && !identity.includes('bey');
            });

            if (voiceAgent) {
              setIsAgentConnected(true);
            }
          }
        };
        checkForAgent();
      }
    }
  }, [audioTracks, room, isAgentConnected, useAvatar]);

  const avatarVideoTrack = useAvatar
    ? videoTracks.find(track => !track.participant.isLocal)
    : undefined;

  useEffect(() => {
    if (isAvatarInitializing) {
      const initToast = toast.loading('Initializing avatar...', {
        duration: Infinity,
      });

      return () => {
        toast.dismiss(initToast);
      };
    }
  }, [isAvatarInitializing]);

  // Show success when fully connected
  useEffect(() => {
    if (isAgentConnected && !isAvatarInitializing) {
      toast.success('Agent connected!', {
        duration: 2000
      });
    }
  }, [isAgentConnected, isAvatarInitializing]);

  return (
    <div className="h-screen flex flex-col lg:flex-row overflow-hidden bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Avatar Initializing Modal */}

      {/* Left Side - Avatar & Call Controls */}
      <div className="w-full lg:w-[60%] flex flex-col items-center justify-center p-4 sm:p-6 lg:p-8 relative">
        {/* Avatar Display */}
        <div className="flex-1 flex items-center justify-center w-full">
          {avatarVideoTrack ? (
            <div className="w-full max-w-[280px] h-[280px] sm:max-w-[360px] sm:h-[360px] lg:max-w-[480px] lg:h-[480px] rounded-3xl overflow-hidden shadow-2xl border border-white/60 bg-black">
              <VideoTrack
                trackRef={avatarVideoTrack}
                className="w-full h-full object-cover"
              />
            </div>
          ) : (
            <div className="flex items-center justify-center">
              <AgentAudioVisualizerAura
                size="xl"
                state={getAgentState()}
                audioTrack={agentAudioTrack}
                color="#1FD5F9"
                colorShift={0.4}
              />
            </div>
          )}
        </div>

        {/* LiveKit Control Bar */}
        <div className="border px-4 sm:px-6 lg:px-8 bg-white shadow-lg rounded-xl w-full max-w-md">
          <ControlBar
            variation="minimal"
            controls={{
              microphone: true,
              camera: false,
              screenShare: false,
              chat: false,
              leave: true
            }}
          />
        </div>
      </div>

      {/* Right Side - Chat Activity Section */}
      <div className="w-full lg:w-[40%] bg-white shadow-2xl flex flex-col overflow-hidden border-t lg:border-t-0 lg:border-l border-gray-200 max-h-[50vh] lg:max-h-none">

        {/* Live Transcript Section */}
        <div className="flex-1 flex flex-col overflow-hidden border-b border-gray-200">
          <div className="px-4 sm:px-6 py-2 sm:py-3 bg-gray-50 border-b border-gray-200">
            <p className="text-xs text-gray-500 mt-0.5">Transcript</p>
          </div>
          <div className="flex-1 overflow-hidden bg-white">
            <LiveTranscript className="h-full" />
          </div>
        </div>

        {/* Tool Calls Section */}
        <div className="flex-shrink-0 bg-white">
          <div className="px-4 sm:px-6 py-2 sm:py-3 bg-gray-50 border-b border-gray-200">
            <p className="text-xs text-gray-500 mt-0.5">Actions performed by the agent</p>
          </div>
          <div className="max-h-40 sm:max-h-60 lg:max-h-80 overflow-y-auto">
            <ToolCallDisplay toolCalls={toolCalls} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default VoiceAgentInterface;
