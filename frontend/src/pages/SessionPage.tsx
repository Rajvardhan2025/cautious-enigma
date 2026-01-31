import { useState, useEffect, useCallback } from 'react';
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
import { fetchLiveKitToken, handleApiError } from '../lib/api';

function SessionPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { roomName, userName } = location.state || {};

  const [token, setToken] = useState('');
  const [livekitUrl, setLivekitUrl] = useState('');
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [conversationSummary, setConversationSummary] = useState<ConversationSummaryData | null>(null);
  const [showSummary, setShowSummary] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getToken = useCallback(async () => {
    if (!roomName || !userName) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await fetchLiveKitToken(roomName, userName);
      setToken(data.token);
      setLivekitUrl(data.url);
    } catch (err) {
      console.error('Error getting token:', err);
      setError(handleApiError(err));
    } finally {
      setIsLoading(false);
    }
  }, [roomName, userName]);

  useEffect(() => {
    if (!roomName || !userName) {
      navigate(ROUTES.HOME);
      return;
    }
    
    if (!token) {
      getToken();
    }
  }, [roomName, userName, token, getToken, navigate]);

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

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">{APP_CONSTANTS.STATUS.CONNECTING}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-gray-800 mb-4">{APP_CONSTANTS.STATUS.ERROR}</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <button
            onClick={() => {
              setError(null);
              getToken();
            }}
            className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-6 rounded-lg transition-colors mr-2"
          >
            Retry Connection
          </button>
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

  if (!token || !livekitUrl) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <LiveKitRoom
        video={false}
        audio={true}
        token={token}
        serverUrl={livekitUrl}
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

export default SessionPage;
