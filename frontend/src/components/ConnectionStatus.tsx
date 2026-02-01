import React from 'react';
import { ConnectionState } from 'livekit-client';
import { Wifi, WifiOff, Loader, CheckCircle, AlertCircle } from 'lucide-react';

interface ConnectionStatusProps {
  connectionState: ConnectionState;
  isAgentConnected: boolean;
}

interface StatusInfo {
  icon: React.ReactNode;
  text: string;
  color: string;
  description: string;
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ connectionState, isAgentConnected }) => {
  const getConnectionInfo = (): StatusInfo => {
    switch (connectionState) {
      case ConnectionState.Connecting:
        return {
          icon: <Loader className="w-4 h-4 animate-spin" />,
          text: 'Connecting...',
          color: 'text-yellow-600 bg-yellow-100',
          description: 'Establishing connection to LiveKit'
        };
      case ConnectionState.Connected:
        return {
          icon: <Wifi className="w-4 h-4" />,
          text: 'Connected',
          color: 'text-green-600 bg-green-100',
          description: 'Connected to LiveKit room'
        };
      case ConnectionState.Disconnected:
        return {
          icon: <WifiOff className="w-4 h-4" />,
          text: 'Disconnected',
          color: 'text-red-600 bg-red-100',
          description: 'Not connected to LiveKit'
        };
      case ConnectionState.Reconnecting:
        return {
          icon: <Loader className="w-4 h-4 animate-spin" />,
          text: 'Reconnecting...',
          color: 'text-yellow-600 bg-yellow-100',
          description: 'Attempting to reconnect'
        };
      default:
        return {
          icon: <AlertCircle className="w-4 h-4" />,
          text: 'Unknown',
          color: 'text-gray-600 bg-gray-100',
          description: 'Connection status unknown'
        };
    }
  };

  const getAgentStatus = (): StatusInfo => {
    if (connectionState !== ConnectionState.Connected) {
      return {
        icon: <AlertCircle className="w-4 h-4" />,
        text: 'Agent Offline',
        color: 'text-gray-600 bg-gray-100',
        description: 'Agent requires room connection'
      };
    }

    return isAgentConnected ? {
      icon: <CheckCircle className="w-4 h-4" />,
      text: 'Agent Ready',
      color: 'text-green-600 bg-green-100',
      description: 'Voice agent is connected and ready'
    } : {
      icon: <Loader className="w-4 h-4 animate-spin" />,
      text: 'Waiting for Agent',
      color: 'text-yellow-600 bg-yellow-100',
      description: 'Waiting for voice agent to join'
    };
  };

  const connectionInfo = getConnectionInfo();
  const agentInfo = getAgentStatus();

  return (
    <div className="flex items-center space-x-2 sm:space-x-4">
      <div className="flex items-center space-x-1 sm:space-x-2">
        <div className={`flex items-center space-x-0.5 sm:space-x-1 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-full text-[10px] sm:text-xs font-medium ${connectionInfo.color}`}>
          <div className="scale-75 sm:scale-100">{connectionInfo.icon}</div>
          <span className="hidden sm:inline">{connectionInfo.text}</span>
        </div>
      </div>

      <div className="flex items-center space-x-1 sm:space-x-2">
        <div className={`flex items-center space-x-0.5 sm:space-x-1 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-full text-[10px] sm:text-xs font-medium ${agentInfo.color}`}>
          <div className="scale-75 sm:scale-100">{agentInfo.icon}</div>
          <span className="hidden sm:inline">{agentInfo.text}</span>
        </div>
      </div>

      <div className="relative group hidden sm:block">
        <button className="text-gray-400 hover:text-gray-600 transition-colors">
          <AlertCircle className="w-4 h-4" />
        </button>
        
        <div className="absolute top-full left-0 mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg p-3 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
          <div className="space-y-2">
            <div>
              <div className="text-xs font-semibold text-gray-700">Room Connection:</div>
              <div className="text-xs text-gray-600">{connectionInfo.description}</div>
            </div>
            <div>
              <div className="text-xs font-semibold text-gray-700">Voice Agent:</div>
              <div className="text-xs text-gray-600">{agentInfo.description}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConnectionStatus;
