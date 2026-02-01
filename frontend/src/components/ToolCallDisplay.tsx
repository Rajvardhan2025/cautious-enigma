import { useState, useEffect } from 'react';
import { 
  Calendar, 
  Search,
  Clock, 
  User, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Edit,
  Trash2,
  MessageSquare
} from 'lucide-react';
import { formatDate } from '../lib/utils';

interface ToolCall {
  id: number;
  tool_name: string;
  parameters?: Record<string, any>;
  result: string;
  status: 'success' | 'error' | 'pending';
  timestamp: Date | string;
}

interface ToolCallDisplayProps {
  toolCalls: ToolCall[];
}

const ToolCallDisplay: React.FC<ToolCallDisplayProps> = ({ toolCalls }) => {
  const [expandedCall, setExpandedCall] = useState<number | null>(null);

  useEffect(() => {
    if (toolCalls.length > 0) {
      const latest = toolCalls[toolCalls.length - 1];
      setExpandedCall(latest.id);
      
      const timer = setTimeout(() => {
        setExpandedCall(null);
      }, 5000);
      
      return () => clearTimeout(timer);
    }
  }, [toolCalls]);

  const getToolIcon = (toolName: string): React.ReactNode => {
    switch (toolName) {
      case 'identify_user':
        return <User className="w-5 h-5" />;
      case 'fetch_slots':
        return <Search className="w-5 h-5" />;
      case 'book_appointment':
        return <Calendar className="w-5 h-5" />;
      case 'retrieve_appointments':
        return <Clock className="w-5 h-5" />;
      case 'cancel_appointment':
        return <Trash2 className="w-5 h-5" />;
      case 'modify_appointment':
        return <Edit className="w-5 h-5" />;
      case 'end_conversation':
        return <MessageSquare className="w-5 h-5" />;
      default:
        return <AlertCircle className="w-5 h-5" />;
    }
  };

  const getToolColor = (toolName: string): string => {
    switch (toolName) {
      case 'identify_user':
        return 'bg-gray-50 text-gray-700 border-gray-200';
      case 'fetch_slots':
        return 'bg-gray-50 text-gray-700 border-gray-200';
      case 'book_appointment':
        return 'bg-gray-50 text-gray-700 border-gray-200';
      case 'retrieve_appointments':
        return 'bg-gray-50 text-gray-700 border-gray-200';
      case 'cancel_appointment':
        return 'bg-gray-50 text-gray-700 border-gray-200';
      case 'modify_appointment':
        return 'bg-gray-50 text-gray-700 border-gray-200';
      case 'end_conversation':
        return 'bg-gray-50 text-gray-700 border-gray-200';
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200';
    }
  };

  const getStatusIcon = (status: string): React.ReactNode => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-gray-600" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-gray-600" />;
      case 'pending':
        return <AlertCircle className="w-4 h-4 text-gray-600 animate-pulse" />;
      default:
        return <CheckCircle className="w-4 h-4 text-gray-600" />;
    }
  };

  const formatToolName = (toolName: string): string => {
    return toolName
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const formatParameters = (params: Record<string, any> | undefined): React.ReactNode => {
    if (!params || Object.keys(params).length === 0) return null;
    
    return Object.entries(params).map(([key, value]) => (
      <div key={key} className="flex justify-between text-xs">
        <span className="font-medium text-gray-600">{key}:</span>
        <span className="text-gray-800 ml-2 truncate">{String(value)}</span>
      </div>
    ));
  };

  const formatTimestamp = (timestamp: Date | string): string => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      });
    } catch (error) {
      return 'Invalid time';
    }
  };

  if (toolCalls.length === 0) {
    return (
      <div className="p-4 sm:p-6 text-center text-gray-400">
        <AlertCircle className="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-3 text-gray-200" />
        <p className="text-xs sm:text-sm">No tool calls yet</p>
        <p className="text-[10px] sm:text-xs mt-1 text-gray-400">Tool calls will appear here as the assistant helps you</p>
      </div>
    );
  }

  return (
    <div className="p-3 sm:p-4 space-y-2 sm:space-y-3">      
      {toolCalls.slice().reverse().map((toolCall) => (
        <div
          key={toolCall.id}
          className={`border border-gray-200 rounded-lg transition-all duration-200 ${
            expandedCall === toolCall.id ? 'shadow-sm' : ''
          }`}
        >
          <div
            className={`p-2.5 sm:p-3 rounded-t-lg border-b border-gray-200 cursor-pointer ${getToolColor(toolCall.tool_name)} hover:bg-gray-100 transition-colors`}
            onClick={() => setExpandedCall(
              expandedCall === toolCall.id ? null : toolCall.id
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center space-x-1.5 sm:space-x-2 min-w-0">
                <div className="flex-shrink-0">
                  {getToolIcon(toolCall.tool_name)}
                </div>
                <span className="font-medium text-xs sm:text-sm truncate">
                  {formatToolName(toolCall.tool_name)}
                </span>
              </div>
              <div className="flex items-center space-x-1.5 sm:space-x-2 flex-shrink-0">
                {getStatusIcon(toolCall.status)}
                <span className="text-[10px] sm:text-xs text-gray-500 hidden sm:inline">
                  {formatTimestamp(toolCall.timestamp)}
                </span>
              </div>
            </div>
          </div>

          {expandedCall === toolCall.id && (
            <div className="p-2.5 sm:p-3 bg-white rounded-b-lg space-y-2 sm:space-y-3">
              {toolCall.parameters && Object.keys(toolCall.parameters).length > 0 && (
                <div>
                  <h4 className="text-[10px] sm:text-xs font-semibold text-gray-500 mb-1.5 sm:mb-2">Parameters:</h4>
                  <div className="bg-gray-50 rounded p-1.5 sm:p-2 space-y-1 border border-gray-100">
                    {formatParameters(toolCall.parameters)}
                  </div>
                </div>
              )}

              <div className="text-[10px] sm:text-xs text-gray-400 pt-1.5 sm:pt-2 border-t border-gray-100">
                Executed at {formatDate(new Date(toolCall.timestamp))}
              </div>
            </div>
          )}
        </div>
      ))}

    </div>
  );
};

export default ToolCallDisplay;
