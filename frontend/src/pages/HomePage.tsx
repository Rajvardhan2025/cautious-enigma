import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../config/constants';
import { createSession, handleApiError } from '../lib/api';
import { AnimatedOrb } from '../components/AnimatedOrb';

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
    <div 
      className="min-h-screen bg-white flex items-center justify-center p-4 relative overflow-hidden cursor-pointer"
      onClick={handleStartSession}
    >
      <div className="relative z-10 flex flex-col items-center justify-center h-full">
        <div className="mb-6 orb-intro">
          <AnimatedOrb size={256} />
        </div>
        <p className="text-2xl font-medium text-stone-400 mb-2">
          Voice Appointment Assistant
        </p>
        <p className="text-sm text-stone-400">
          Click anywhere to get started
        </p>
        
        {error && (
          <div className="mt-6 p-4 bg-red-500/20 border border-red-400/50 text-red-800 rounded-xl max-w-md">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}

export default HomePage;
