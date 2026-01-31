import { useState, useEffect } from 'react';
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

import AvatarDisplay from './AvatarDisplay';
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

  useEffect(() => {
    if (!room) return;

    const checkForAgent = () => {
      const participants = Array.from(room.remoteParticipants.values());
      const agentPresent = participants.some(p =>
        APP_CONSTANTS.AGENT_IDENTITY_KEYWORDS.some(keyword =>
          p.identity.toLowerCase().includes(keyword)
        )
      );
      if (agentPresent) {
        console.log('Agent already in room');
        setIsAgentConnected(true);
      }
    };

    checkForAgent();

    const handleParticipantConnected = (participant: Participant) => {
      console.log('Participant connected:', participant.identity);
      if (APP_CONSTANTS.AGENT_IDENTITY_KEYWORDS.some(keyword =>
        participant.identity.toLowerCase().includes(keyword)
      )) {
        setIsAgentConnected(true);
      }
    };

    const handleParticipantDisconnected = (participant: Participant) => {
      console.log('Participant disconnected:', participant.identity);
      if (APP_CONSTANTS.AGENT_IDENTITY_KEYWORDS.some(keyword =>
        participant.identity.toLowerCase().includes(keyword)
      )) {
        setIsAgentConnected(false);
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
  }, [room, onToolCall, onConversationEnd, onEndCall]);

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
    <div className="h-screen flex flex-col overflow-hidden bg-gradient-to-br from-slate-50 to-slate-100">

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden relative">
        {useAvatar && isAvatarInitializing && !avatarVideoTrack && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/40 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-xl p-6 w-[420px] max-w-[90%] text-center">
              <div className="text-lg font-semibold text-gray-800">Initializing avatar…</div>
              <p className="text-sm text-gray-600 mt-2">
                You can start the conversation now and enable the avatar later.
              </p>
              <div className="mt-4 flex items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => setUseAvatar(false)}
                  className="px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-800 text-sm font-medium"
                >
                  Continue without avatar
                </button>
                <button
                  type="button"
                  onClick={() => setIsAvatarInitializing(false)}
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium"
                >
                  Keep waiting
                </button>
              </div>
            </div>
          </div>
        )}
        {/* Main Area - Avatar & Status */}
        <div className="flex-1 flex items-center justify-center p-8 pb-32">
          {avatarVideoTrack ? (
            <div className="w-[420px] h-[420px] rounded-3xl overflow-hidden shadow-2xl border border-white/60 bg-black">
              <VideoTrack
                trackRef={avatarVideoTrack}
                className="w-full h-full object-cover"
              />
            </div>
          ) : (
            <AvatarDisplay
              isListening={isListening}
              isSpeaking={isSpeaking}
              isConnected={isAgentConnected}
            />
          )}
        </div>

        {/* Floating Chat Panel */}
        <div className="absolute right-6 top-6 bottom-6 w-96 bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-gray-200">
          <div className="bg-gradient-to-r from-blue-500 to-indigo-600 px-5 py-4 flex-shrink-0">
            <h2 className="text-sm font-semibold text-white">Live Conversation</h2>
            <p className="text-xs text-blue-100 mt-0.5">Real-time transcript</p>
          </div>

          <div className="flex-1 overflow-hidden bg-gradient-to-b from-gray-50 to-white">
            <LiveTranscript className="h-full" />
          </div>

          <div className="border-t bg-white">
            <div className="px-5 py-3">
              <h3 className="text-sm font-semibold text-gray-700">Tool Calls</h3>
              <p className="text-xs text-gray-500 mt-0.5">Actions performed by the agent</p>
            </div>
            <div className="max-h-72 overflow-y-auto">
              <ToolCallDisplay toolCalls={toolCalls} />
            </div>
          </div>
        </div>

        {/* LiveKit Control Bar */}
        <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 z-20" style={{ marginRight: '200px' }}>
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
    </div>
  );
}

export default VoiceAgentInterface;
