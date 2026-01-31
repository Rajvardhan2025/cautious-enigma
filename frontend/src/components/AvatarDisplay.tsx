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
    <div className="flex flex-col items-center space-y-8">
      <div className={`relative p-6 rounded-full border-4 transition-all duration-300 ${styles.container} shadow-lg`}>
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
          className={`relative w-40 h-40 rounded-full flex items-center justify-center transition-all duration-200 ${styles.avatar}`}
          style={{
            transform: `scale(${speakingScale})`
          }}
        >
          {state === 'connecting' ? (
            <Loader className="w-20 h-20 animate-spin" />
          ) : (
            <User className="w-20 h-20" />
          )}
        </div>

        {isSpeaking && (
          <>
            <div className="absolute inset-0 rounded-full border-2 border-blue-300 animate-ping opacity-75" />
            <div className="absolute inset-2 rounded-full border-2 border-blue-400 animate-ping opacity-50" style={{ animationDelay: '0.2s' }} />
          </>
        )}

        {isListening && (
          <div className="absolute -bottom-2 -right-2 w-10 h-10 bg-green-500 rounded-full flex items-center justify-center shadow-lg">
            <div className="w-4 h-4 bg-white rounded-full animate-pulse" />
          </div>
        )}
      </div>

      <div className="text-center">
        <p className={`text-2xl font-bold mb-1 ${
          state === 'connecting' ? 'text-yellow-600' :
          state === 'speaking' ? 'text-blue-600' :
          state === 'listening' ? 'text-green-600' :
          'text-gray-600'
        }`}>
          {state === 'connecting' && 'Connecting...'}
          {state === 'speaking' && 'Speaking'}
          {state === 'listening' && 'Listening'}
          {state === 'idle' && 'Ready to Help'}
        </p>
        <p className="text-sm text-gray-500">
          {state === 'connecting' && 'Establishing connection'}
          {state === 'speaking' && 'AI is responding'}
          {state === 'listening' && 'Waiting for your input'}
          {state === 'idle' && 'Start speaking to begin'}
        </p>
      </div>
    </div>
  );
};

export default AvatarDisplay;
