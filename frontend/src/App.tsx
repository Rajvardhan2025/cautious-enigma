import { useState, useEffect, useCallback } from 'react';
import { 
  LiveKitRoom, 
  RoomAudioRenderer, 
  useRoomContext,
  useConnectionState,
  useTracks
} from '@livekit/components-react';
import { 
  RoomEvent, 
  Track,
  Participant
} from 'livekit-client';
import '@livekit/components-styles';

import VoiceInterface from './components/VoiceInterface';
import AvatarDisplay from './components/AvatarDisplay';
import ToolCallDisplay from './components/ToolCallDisplay';
import ConversationSummary from './components/ConversationSummary';
import ConnectionStatus from './components/ConnectionStatus';

const LIVEKIT_URL = import.meta.env.VITE_LIVEKIT_URL || 'wss://your-livekit-server.livekit.cloud';
const LIVEKIT_TOKEN_URL = import.meta.env.VITE_LIVEKIT_TOKEN_URL || '/api/token';

interface ToolCall {
  id: number;
  tool_name: string;
  parameters?: Record<string, any>;
  result: string;
  status: 'success' | 'error' | 'pending';
  timestamp: Date;
  type?: string;
}

interface TranscriptItem {
  text: string;
  timestamp?: Date;
  speaker?: string;
  type?: string;
}

interface ConversationSummaryData {
  conversation_date: string;
  duration_minutes?: number;
  appointments_discussed?: Array<{
    date: string;
    time: string;
    purpose?: string;
    status?: string;
  }>;
  user_preferences?: string[];
  summary_text: string;
  user_phone?: string;
}

function App() {
  const [token, setToken] = useState('');
  const [roomName, setRoomName] = useState('');
  const [userName, setUserName] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [conversationSummary, setConversationSummary] = useState<ConversationSummaryData | null>(null);
  const [showSummary, setShowSummary] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const generateRoomName = () => `voice-agent-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const generateUserName = () => `user-${Math.random().toString(36).substr(2, 9)}`;
    
    setRoomName(generateRoomName());
    setUserName(generateUserName());
  }, []);

  const getToken = useCallback(async () => {
    if (!roomName || !userName) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(LIVEKIT_TOKEN_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          roomName,
          participantName: userName,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to get token: ${response.statusText}`);
      }

      const data = await response.json();
      setToken(data.token);
    } catch (err) {
      console.error('Error getting token:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setToken('mock-token-for-development');
    } finally {
      setIsLoading(false);
    }
  }, [roomName, userName]);

  useEffect(() => {
    if (roomName && userName && !token) {
      getToken();
    }
  }, [roomName, userName, token, getToken]);

  const handleConnect = async () => {
    if (token) {
      setIsConnected(true);
    } else {
      await getToken();
      // Add a small delay to ensure agent has time to register
      setTimeout(() => {
        setIsConnected(true);
      }, 2000);
    }
  };

  const handleDisconnect = () => {
    setIsConnected(false);
    setToolCalls([]);
    setConversationSummary(null);
    setShowSummary(false);
  };

  const handleToolCall = (toolCall: Omit<ToolCall, 'id' | 'timestamp'>) => {
    setToolCalls(prev => [...prev, {
      ...toolCall,
      id: Date.now(),
      timestamp: new Date()
    }]);
  };

  const handleConversationEnd = (summary: ConversationSummaryData) => {
    setConversationSummary(summary);
    setShowSummary(true);
  };

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Connection Error</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => {
              setError(null);
              getToken();
            }}
            className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-6 rounded-lg transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  if (!isConnected) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="text-blue-500 text-6xl mb-4">🎤</div>
          <h1 className="text-3xl font-bold text-gray-800 mb-4">Voice Appointment Assistant</h1>
          <p className="text-gray-600 mb-8">
            Connect to start booking appointments with our AI voice assistant. 
            The assistant can help you book, modify, or cancel appointments through natural conversation.
          </p>
          
          <div className="space-y-4 mb-8">
            <div className="text-left">
              <label className="block text-sm font-medium text-gray-700 mb-1">Room ID</label>
              <input
                type="text"
                value={roomName}
                onChange={(e) => setRoomName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter room name"
              />
            </div>
            <div className="text-left">
              <label className="block text-sm font-medium text-gray-700 mb-1">Your Name</label>
              <input
                type="text"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter your name"
              />
            </div>
          </div>

          <button
            onClick={handleConnect}
            disabled={isLoading || !roomName || !userName}
            className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
          >
            {isLoading ? 'Connecting...' : 'Start Voice Session'}
          </button>

          <div className="mt-6 text-sm text-gray-500">
            <p>Features:</p>
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>Natural voice conversation</li>
              <li>Real-time appointment booking</li>
              <li>Visual avatar display</li>
              <li>Conversation summaries</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <LiveKitRoom
        video={false}
        audio={true}
        token={token}
        serverUrl={LIVEKIT_URL}
        data-lk-theme="default"
        style={{ height: '100vh' }}
        onConnected={() => console.log('Connected to room')}
        onDisconnected={handleDisconnect}
        onError={(error) => {
          console.error('Room error:', error);
          setError(error.message);
        }}
      >
        <VoiceAgentInterface
          onToolCall={handleToolCall}
          onConversationEnd={handleConversationEnd}
          toolCalls={toolCalls}
          onDisconnect={handleDisconnect}
        />
        <RoomAudioRenderer />
      </LiveKitRoom>

      {showSummary && conversationSummary && (
        <ConversationSummary
          summary={conversationSummary}
          onClose={() => setShowSummary(false)}
        />
      )}
    </div>
  );
}

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

    // Check if agent is already in the room
    const checkForAgent = () => {
      const participants = Array.from(room.remoteParticipants.values());
      const agentPresent = participants.some(p => 
        p.identity.toLowerCase().includes('agent') || 
        p.identity.toLowerCase().includes('voice')
      );
      if (agentPresent) {
        console.log('Agent already in room');
        setIsAgentConnected(true);
      }
    };

    // Check immediately
    checkForAgent();

    const handleParticipantConnected = (participant: Participant) => {
      console.log('Participant connected:', participant.identity);
      if (participant.identity.toLowerCase().includes('agent') || 
          participant.identity.toLowerCase().includes('voice')) {
        setIsAgentConnected(true);
      }
    };

    const handleParticipantDisconnected = (participant: Participant) => {
      console.log('Participant disconnected:', participant.identity);
      if (participant.identity.toLowerCase().includes('agent') || 
          participant.identity.toLowerCase().includes('voice')) {
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

export default App;
