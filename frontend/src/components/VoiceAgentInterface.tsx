import { useState, useEffect } from 'react';
import {
  useRoomContext,
  useConnectionState,
  useTracks,
  useLocalParticipant,
  ControlBar,
  useMaybeRoomContext
} from '@livekit/components-react';
import {
  RoomEvent,
  Track,
  Participant
} from 'livekit-client';

import AvatarDisplay from './AvatarDisplay';
import LiveTranscript from './LiveTranscript';
import ConnectionStatus from './ConnectionStatus';
import ToolCallDisplay from './ToolCallDisplay';
import { ToolCall, ConversationSummaryData, TranscriptItem } from '../types';
import { APP_CONSTANTS } from '../config/constants';

interface VoiceAgentInterfaceProps {
  onToolCall: (toolCall: Omit<ToolCall, 'id' | 'timestamp'>) => void;
  onConversationEnd: (summary: ConversationSummaryData) => void;
  onEndCall: () => void;
  toolCalls: ToolCall[];
  onDisconnect: () => void;
}

function VoiceAgentInterface({ onToolCall, onConversationEnd, onEndCall, toolCalls, onDisconnect }: VoiceAgentInterfaceProps) {
  const room = useRoomContext();
  const connectionState = useConnectionState();
  const tracks = useTracks([Track.Source.Microphone, Track.Source.ScreenShare]);

  const [isAgentConnected, setIsAgentConnected] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

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
        } else if (data.type === 'transcript') {
          setTranscript(prev => [...prev, data]);
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
  }, [room, onToolCall, onConversationEnd]);

  useEffect(() => {
    const audioTracks = tracks.filter(track => track.source === Track.Source.Microphone);

    audioTracks.forEach(track => {
      if (track.participant.isLocal) {
        setIsListening(track.publication?.track?.isMuted === false);
      } else {
        setIsSpeaking(track.publication?.track?.isMuted === false);
      }
    });
  }, [tracks]);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <div className="bg-white shadow-sm border-b px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white text-xl">🎤</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Voice Assistant</h1>
                <p className="text-xs text-gray-500">AI-Powered Appointment Booking</p>
              </div>
            </div>
            <ConnectionStatus
              connectionState={connectionState}
              isAgentConnected={isAgentConnected}
            />
          </div>
          <button
            onClick={onDisconnect}
            className="bg-red-500 hover:bg-red-600 text-white px-5 py-2.5 rounded-lg transition-all hover:shadow-lg font-medium text-sm"
          >
            End Session
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Main Area - Avatar & Status */}
        <div className="flex-1 flex items-center justify-center p-8 pb-32">
          <AvatarDisplay
            isListening={isListening}
            isSpeaking={isSpeaking}
            isConnected={isAgentConnected}
          />
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

        {/* Floating Control Bar */}
        <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 z-20" style={{ marginRight: '200px' }}>
          <ControlBar
            variation="minimal"
            controls={{
              microphone: true,
              camera: false,
              screenShare: false,
              chat: false,
              leave: false
            }}
          />
        </div>
      </div>
    </div>
  );
}

export default VoiceAgentInterface;
