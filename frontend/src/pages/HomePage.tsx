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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-indigo-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
      </div>

      <div className="relative z-10 max-w-4xl w-full">
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl shadow-2xl mb-6 transform hover:scale-110 transition-transform">
            <span className="text-4xl">🎤</span>
          </div>
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-4 tracking-tight">
            Voice Appointment Assistant
          </h1>
          <p className="text-xl text-blue-200 max-w-2xl mx-auto">
            Book, modify, or cancel appointments through natural conversation with our AI-powered voice assistant
          </p>
        </div>

        <div className="bg-white/10 backdrop-blur-lg rounded-3xl shadow-2xl p-8 border border-white/20">
          {error && (
            <div className="mb-6 p-4 bg-red-500/20 border border-red-400/50 text-red-100 rounded-xl backdrop-blur-sm">
              {error}
            </div>
          )}

          <button
            onClick={handleStartSession}
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-semibold py-4 px-8 rounded-xl transition-all transform hover:scale-105 hover:shadow-2xl disabled:hover:scale-100 text-lg"
          >
            {isLoading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Connecting...
              </span>
            ) : (
              'Start Voice Session'
            )}
          </button>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
            {FEATURES.map((feature, index) => (
              <div key={index} className="flex items-center space-x-3 text-white/90 bg-white/5 rounded-xl p-4 backdrop-blur-sm border border-white/10">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-500/30 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-blue-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <span className="text-sm font-medium">{feature}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-8 text-center">
          <p className="text-blue-200 text-sm">
            Powered by AI • Secure & Private • Available 24/7
          </p>
        </div>
      </div>
    </div>
  );
}

export default HomePage;
