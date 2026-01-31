import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  LiveKitRoom, 
  RoomAudioRenderer
} from '@livekit/components-react';
import '@livekit/components-styles';

import VoiceAgentInterface from '../components/VoiceAgentInterface';
import ConversationSummary from '../components/ConversationSummary';
import { ToolCall, ConversationSummaryData } from '../types';
import { ROUTES, APP_CONSTANTS } from '../config/constants';

function SessionPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { token, url, roomName, participantName } = location.state || {};

  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [conversationSummary, setConversationSummary] = useState<ConversationSummaryData | null>(null);
  const [showSummary, setShowSummary] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !url || !roomName) {
      navigate(ROUTES.HOME);
    }
  }, [token, url, roomName, navigate]);

  const handleDisconnect = () => {
    navigate(ROUTES.HOME);
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
          <h2 className="text-2xl font-bold text-gray-800 mb-4">{APP_CONSTANTS.STATUS.ERROR}</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={handleDisconnect}
            className="bg-gray-500 hover:bg-gray-600 text-white font-semibold py-2 px-6 rounded-lg transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  if (!token || !url) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <LiveKitRoom
        video={false}
        audio={true}
        token={token}
        serverUrl={url}
        data-lk-theme="default"
        style={{ height: '100vh' }}
        onConnected={() => console.log('Connected to room:', roomName)}
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

export default SessionPage;
