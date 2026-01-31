import { useState, useEffect } from 'react';
import { Mic, MicOff, Volume2, VolumeX } from 'lucide-react';

interface TranscriptItem {
  text: string;
  timestamp?: Date;
  speaker?: string;
}

interface VoiceInterfaceProps {
  isListening: boolean;
  isSpeaking: boolean;
  isConnected: boolean;
  transcript: TranscriptItem[];
}

const VoiceInterface: React.FC<VoiceInterfaceProps> = ({ 
  isListening, 
  isSpeaking, 
  isConnected, 
  transcript 
}) => {
  const [audioLevel, setAudioLevel] = useState(0);
  const [lastTranscript, setLastTranscript] = useState('');

  useEffect(() => {
    if (isListening || isSpeaking) {
      const interval = setInterval(() => {
        setAudioLevel(Math.random() * 100);
      }, 100);
      return () => clearInterval(interval);
    } else {
      setAudioLevel(0);
    }
  }, [isListening, isSpeaking]);

  useEffect(() => {
    if (transcript.length > 0) {
      const latest = transcript[transcript.length - 1];
      setLastTranscript(latest.text || '');
    }
  }, [transcript]);

  const getStatusText = (): string => {
    if (!isConnected) return 'Waiting for assistant to join...';
    if (isSpeaking) return 'Assistant is speaking...';
    if (isListening) return 'Listening...';
    return 'Ready to listen';
  };

  const getStatusColor = (): string => {
    if (!isConnected) return 'text-yellow-600';
    if (isSpeaking) return 'text-blue-600';
    if (isListening) return 'text-green-600';
    return 'text-gray-600';
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="flex items-center justify-center space-x-4 mb-4">
          <div className="flex items-center space-x-2">
            {isListening ? (
              <Mic className="w-6 h-6 text-green-500" />
            ) : (
              <MicOff className="w-6 h-6 text-gray-400" />
            )}
            <span className="text-sm text-gray-600">
              {isListening ? 'Mic On' : 'Mic Off'}
            </span>
          </div>

          <div className="flex items-center space-x-2">
            {isSpeaking ? (
              <Volume2 className="w-6 h-6 text-blue-500" />
            ) : (
              <VolumeX className="w-6 h-6 text-gray-400" />
            )}
            <span className="text-sm text-gray-600">
              {isSpeaking ? 'Speaking' : 'Silent'}
            </span>
          </div>
        </div>

        <p className={`text-lg font-medium ${getStatusColor()}`}>
          {getStatusText()}
        </p>
      </div>

      {lastTranscript && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Last Message:</h3>
          <p className="text-gray-800">{lastTranscript}</p>
        </div>
      )}

      <div className="text-center text-sm text-gray-500">
        <p>Speak naturally to book, modify, or cancel appointments.</p>
        <p className="mt-1">The assistant will guide you through the process.</p>
      </div>

      <div className="flex items-center justify-center space-x-2">
        <div className={`w-3 h-3 rounded-full ${
          isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
        }`} />
        <span className="text-sm text-gray-600">
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
      </div>
    </div>
  );
};

export default VoiceInterface;
