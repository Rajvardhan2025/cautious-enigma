import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES, FEATURES, APP_CONSTANTS } from '../config/constants';

function HomePage() {
  const navigate = useNavigate();
  const [roomName, setRoomName] = useState('');
  const [userName, setUserName] = useState('');

  useEffect(() => {
    const generateRoomName = () => `${APP_CONSTANTS.ROOM_PREFIX}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const generateUserName = () => `${APP_CONSTANTS.USER_PREFIX}-${Math.random().toString(36).substr(2, 9)}`;
    
    setRoomName(generateRoomName());
    setUserName(generateUserName());
  }, []);

  const handleStartSession = () => {
    if (roomName && userName) {
      navigate(ROUTES.SESSION, { state: { roomName, userName } });
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
          onClick={handleStartSession}
          disabled={!roomName || !userName}
          className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
        >
          Start Voice Session
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
