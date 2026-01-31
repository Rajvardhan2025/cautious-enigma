// This component is no longer needed as we're using LiveKit's ControlBar
// Keeping it for backward compatibility but it won't be rendered
import { useState, useEffect } from 'react';

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

const VoiceInterface: React.FC<VoiceInterfaceProps> = () => {
  return null;
};

export default VoiceInterface;
