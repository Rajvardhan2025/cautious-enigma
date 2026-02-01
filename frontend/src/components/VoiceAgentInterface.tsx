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
import { Toaster } from '@/components/ui/sonner';

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
    if (!isAgentConnected && connectingToastRef.current === null) {
      connectingToastRef.current = toast.loading('Connecting to agent...', {
        duration: Infinity,
      });
    } else if (isAgentConnected && connectingToastRef.current !== null) {
      toast.success('Agent connected!', {
        id: connectingToastRef.current,
        duration: 2000
      });
      connectingToastRef.current = null;
    }
  }, [isAgentConnected]);

  useEffect(() => {
    if (!room) return;

    const checkForAgent = () => {
      const participants = Array.from(room.remoteParticipants.values());
      console.log('All participants in room:', participants.map(p => ({ identity: p.identity, name: p.name })));

      // When using avatar, we need both voice agent and avatar agent
      if (useAvatar) {
        const hasVoiceAgent = participants.some(p => 
          p.identity.toLowerCase().includes('voice') || 
          p.identity.toLowerCase().includes('agent')
        );
        const hasAvatarAgent = participants.some(p => 
          p.identity.toLowerCase().includes('bey') || 
          p.identity.toLowerCase().includes('avatar')
        );
        
        if (hasVoiceAgent && hasAvatarAgent) {
          console.log('Both voice agent and avatar agent detected in room');
          setIsAgentConnected(true);
        } else {
          console.log(`Waiting for agents - Voice: ${hasVoiceAgent}, Avatar: ${hasAvatarAgent}`);
        }
      } else {
        // Without avatar, just need the voice agent
        const agentPresent = participants.some(p => {
          const matchesKeyword = APP_CONSTANTS.AGENT_IDENTITY_KEYWORDS.some(keyword =>
            p.identity.toLowerCase().includes(keyword)
          );
          return matchesKeyword;
        });

        if (agentPresent) {
          console.log('Voice agent detected in room');
          setIsAgentConnected(true);
        }
      }
    };

    checkForAgent();

    const handleParticipantConnected = (participant: Participant) => {
      console.log('Participant connected:', { identity: participant.identity, name: participant.name, isLocal: participant.isLocal });
      
      // Re-check agent status whenever a participant connects
      checkForAgent();
    };

    const handleParticipantDisconnected = (participant: Participant) => {
      console.log('Participant disconnected:', participant.identity);
      
      // Re-check agent status when someone disconnects
      const participants = Array.from(room.remoteParticipants.values());
      
      if (useAvatar) {
        const hasVoiceAgent = participants.some(p => 
          p.identity.toLowerCase().includes('voice') || 
          p.identity.toLowerCase().includes('agent')
        );
        const hasAvatarAgent = participants.some(p => 
          p.identity.toLowerCase().includes('bey') || 
          p.identity.toLowerCase().includes('avatar')
        );
        
        if (!hasVoiceAgent || !hasAvatarAgent) {
          setIsAgentConnected(false);
        }
      } else {
        const agentPresent = participants.some(p => 
          APP_CONSTANTS.AGENT_IDENTITY_KEYWORDS.some(keyword =>
            p.identity.toLowerCase().includes(keyword)
          )
        );
        
        if (!agentPresent) {
          setIsAgentConnected(false);
        }
      }
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
        console.error('Error parsing data:', error);
      }
    };

    room.on(RoomEvent.ParticipantConnected, handleParticipantConnected);
    room.on(RoomEvent.ParticipantDisconnected, handleParticipantDisconnected);
    room.on(RoomEvent.DataReceived, handleDataReceived);

    return () => {
      room.off(RoomEvent.ParticipantConnected, handleParticipantConnected);
      room.off(RoomEvent.ParticipantDisconnected, handleParticipantDisconnected);
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
  }, [audioTracks]);

  const avatarVideoTrack = useAvatar
    ? videoTracks.find(track => !track.participant.isLocal)
    : undefined;

  useEffect(() => {
    if (!useAvatar) {
      setIsAvatarInitializing(false);
      return;
    }

    if (avatarVideoTrack) {
      setIsAvatarInitializing(false);
      return;
    }

    if (isAgentConnected) {
      setIsAvatarInitializing(true);
    }
  }, [useAvatar, avatarVideoTrack, isAgentConnected]);

  return (
    <div className="h-screen flex flex-col lg:flex-row overflow-hidden bg-gradient-to-br from-slate-50 to-slate-100">
      <Toaster position="top-center" />
      
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
