import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES, FEATURES } from '../config/constants';
import { createSession, handleApiError } from '../lib/api';

function HomePage() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartSession = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const session = await createSession();
      navigate(ROUTES.SESSION, { 
        state: { 
          token: session.token,
          url: session.url,
          roomName: session.roomName,
          participantName: session.participantName
        } 
      });
    } catch (err) {
      console.error('Error creating session:', err);
      setError(handleApiError(err));
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
        <div className="text-blue-500 text-6xl mb-4">🎤</div>
        <h1 className="text-3xl font-bold text-gray-800 mb-4">Voice Appointment Assistant</h1>
        <p className="text-gray-600 mb-8">
          Connect to start booking appointments with our AI voice assistant. 
          The assistant can help you book, modify, or cancel appointments through natural conversation.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        <button
          onClick={handleStartSession}
          disabled={isLoading}
          className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
        >
          {isLoading ? 'Connecting...' : 'Start Voice Session'}
        </button>

        <div className="mt-6 text-sm text-gray-500">
          <p>Features:</p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            {FEATURES.map((feature, index) => (
              <li key={index}>{feature}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

export default HomePage;
