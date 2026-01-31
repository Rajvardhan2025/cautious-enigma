import { useState, useEffect } from 'react';
import { User, Loader } from 'lucide-react';

interface AvatarDisplayProps {
  isListening: boolean;
  isSpeaking: boolean;
  isConnected: boolean;
}

type AvatarState = 'connecting' | 'speaking' | 'listening' | 'idle';

interface AvatarStyles {
  container: string;
  avatar: string;
  glow: string;
}

const AvatarDisplay: React.FC<AvatarDisplayProps> = ({ isListening, isSpeaking, isConnected }) => {
  const [animationFrame, setAnimationFrame] = useState(0);

  useEffect(() => {
    if (isSpeaking) {
      const interval = setInterval(() => {
        setAnimationFrame(prev => (prev + 1) % 60);
      }, 50);
      return () => clearInterval(interval);
    }
  }, [isSpeaking]);

  const getAvatarState = (): AvatarState => {
    if (!isConnected) return 'connecting';
    if (isSpeaking) return 'speaking';
    if (isListening) return 'listening';
    return 'idle';
  };

  const getAvatarStyles = (): AvatarStyles => {
    const state = getAvatarState();
    
    switch (state) {
      case 'connecting':
        return {
          container: 'bg-yellow-100 border-yellow-300',
          avatar: 'bg-yellow-200 text-yellow-600',
          glow: 'shadow-yellow-200'
        };
      case 'speaking':
        return {
          container: 'bg-blue-100 border-blue-300',
          avatar: 'bg-blue-200 text-blue-600',
          glow: 'shadow-blue-200'
        };
      case 'listening':
        return {
          container: 'bg-green-100 border-green-300',
          avatar: 'bg-green-200 text-green-600',
          glow: 'shadow-green-200'
        };
      default:
        return {
          container: 'bg-gray-100 border-gray-300',
          avatar: 'bg-gray-200 text-gray-600',
          glow: 'shadow-gray-200'
        };
    }
  };

  const styles = getAvatarStyles();
  const state = getAvatarState();

  const speakingScale = isSpeaking ? 
    1 + Math.sin(animationFrame * 0.3) * 0.1 : 1;

  return (
    <div className="flex flex-col items-center space-y-6">
      <div className={`relative p-8 rounded-full border-4 transition-all duration-300 ${styles.container}`}>
        <div 
          className={`absolute inset-0 rounded-full transition-all duration-300 ${styles.glow}`}
          style={{
            boxShadow: state === 'speaking' ? 
              `0 0 ${20 + Math.sin(animationFrame * 0.2) * 10}px ${styles.glow.split('-')[1]}-400` :
              state === 'listening' ? 
              `0 0 15px ${styles.glow.split('-')[1]}-400` : 
              'none'
          }}
        />
        
        <div 
          className={`relative w-32 h-32 rounded-full flex items-center justify-center transition-all duration-200 ${styles.avatar}`}
          style={{
            transform: `scale(${speakingScale})`
          }}
        >
          {state === 'connecting' ? (
            <Loader className="w-16 h-16 animate-spin" />
          ) : (
            <User className="w-16 h-16" />
          )}
        </div>

        {isSpeaking && (
          <>
            <div className="absolute inset-0 rounded-full border-2 border-blue-300 animate-ping opacity-75" />
            <div className="absolute inset-2 rounded-full border-2 border-blue-400 animate-ping opacity-50" style={{ animationDelay: '0.2s' }} />
          </>
        )}

        {isListening && (
          <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
            <div className="w-3 h-3 bg-white rounded-full animate-pulse" />
          </div>
        )}
      </div>

      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          Voice Assistant
        </h2>
        <p className={`text-lg font-medium ${
          state === 'connecting' ? 'text-yellow-600' :
          state === 'speaking' ? 'text-blue-600' :
          state === 'listening' ? 'text-green-600' :
          'text-gray-600'
        }`}>
          {state === 'connecting' && 'Connecting...'}
          {state === 'speaking' && 'Speaking'}
          {state === 'listening' && 'Listening'}
          {state === 'idle' && 'Ready'}
        </p>
      </div>

      <div className="text-center text-sm text-gray-500 max-w-md">
        <p>
          This is where the Beyond Presence or Tavus avatar will be displayed.
          The avatar will sync with the voice output for a more engaging experience.
        </p>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 max-w-md">
        <h3 className="text-sm font-semibold text-blue-800 mb-2">Avatar Integration</h3>
        <p className="text-xs text-blue-700">
          To enable avatar display:
          <br />• Configure Beyond Presence or Tavus API keys
          <br />• Replace this component with avatar video stream
          <br />• Sync avatar speech with TTS output
        </p>
      </div>
    </div>
  );
};

export default AvatarDisplay;
