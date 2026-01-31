import { useState, useEffect } from 'react';
import { 
  useRoomContext,
  useConnectionState,
  useTracks
} from '@livekit/components-react';
import { 
  RoomEvent, 
  Track,
  Participant
} from 'livekit-client';

import VoiceInterface from './VoiceInterface';
import AvatarDisplay from './AvatarDisplay';
import ToolCallDisplay from './ToolCallDisplay';
import ConnectionStatus from './ConnectionStatus';
import { ToolCall, ConversationSummaryData, TranscriptItem } from '../types';
import { APP_CONSTANTS } from '../config/constants';

interface VoiceAgentInterfaceProps {
  onToolCall: (toolCall: Omit<ToolCall, 'id' | 'timestamp'>) => void;
  onConversationEnd: (summary: ConversationSummaryData) => void;
  toolCalls: ToolCall[];
  onDisconnect: () => void;
}

function VoiceAgentInterface({ onToolCall, onConversationEnd, toolCalls, onDisconnect }: VoiceAgentInterfaceProps) {
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
    <div className="h-screen flex flex-col">
      <div className="bg-white shadow-sm border-b p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-gray-800">Voice Assistant</h1>
            <ConnectionStatus 
              connectionState={connectionState}
              isAgentConnected={isAgentConnected}
            />
          </div>
          <button
            onClick={onDisconnect}
            className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg transition-colors"
          >
            End Session
          </button>
        </div>
      </div>

      <div className="flex-1 flex">
        <div className="flex-1 flex flex-col">
          <div className="flex-1 flex items-center justify-center p-8">
            <AvatarDisplay 
              isListening={isListening}
              isSpeaking={isSpeaking}
              isConnected={isAgentConnected}
            />
          </div>
          
          <div className="p-6 bg-white border-t">
            <VoiceInterface
              isListening={isListening}
              isSpeaking={isSpeaking}
              isConnected={isAgentConnected}
              transcript={transcript}
            />
          </div>
        </div>

        <div className="w-96 bg-white border-l flex flex-col">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold text-gray-800">Activity</h2>
          </div>
          
          <div className="flex-1 overflow-y-auto">
            <ToolCallDisplay toolCalls={toolCalls} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default VoiceAgentInterface;
