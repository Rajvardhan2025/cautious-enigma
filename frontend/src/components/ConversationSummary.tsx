import React from 'react';
import { 
  X, 
  Calendar, 
  Clock, 
  User, 
  MessageSquare, 
  CheckCircle,
  Download,
  Share
} from 'lucide-react';
import { formatDate } from '../lib/utils';

interface Appointment {
  date: string;
  time: string;
  purpose?: string;
  status?: string;
}

interface ConversationSummaryData {
  conversation_date: string;
  duration_minutes?: number;
  appointments_discussed?: Appointment[];
  user_preferences?: string[];
  summary_text: string;
  user_phone?: string;
}

interface ConversationSummaryProps {
  summary: ConversationSummaryData;
  onClose: () => void;
}

const ConversationSummary: React.FC<ConversationSummaryProps> = ({ summary, onClose }) => {
  const handleDownload = () => {
    const summaryText = generateSummaryText(summary);
    const blob = new Blob([summaryText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-summary-${new Date().toISOString().slice(0, 16).replace(/:/g, '-')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleShare = async () => {
    const summaryText = generateSummaryText(summary);
    
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Conversation Summary',
          text: summaryText,
        });
      } catch (error) {
        console.log('Error sharing:', error);
        copyToClipboard(summaryText);
      }
    } else {
      copyToClipboard(summaryText);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      alert('Summary copied to clipboard!');
    });
  };

  const generateSummaryText = (summary: ConversationSummaryData): string => {
    let text = `CONVERSATION SUMMARY\n`;
    text += `Date: ${formatDate(new Date(summary.conversation_date))}\n`;
    text += `Duration: ${summary.duration_minutes || 'N/A'} minutes\n\n`;
    
    if (summary.appointments_discussed && summary.appointments_discussed.length > 0) {
      text += `APPOINTMENTS DISCUSSED:\n`;
      summary.appointments_discussed.forEach((apt, index) => {
        text += `${index + 1}. ${apt.date} at ${apt.time} - ${apt.purpose}\n`;
      });
      text += `\n`;
    }
    
    if (summary.user_preferences && summary.user_preferences.length > 0) {
      text += `USER PREFERENCES:\n`;
      summary.user_preferences.forEach((pref) => {
        text += `• ${pref}\n`;
      });
      text += `\n`;
    }
    
    text += `SUMMARY:\n${summary.summary_text}\n`;
    
    return text;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        <div className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <MessageSquare className="w-8 h-8" />
              <div>
                <h2 className="text-2xl font-bold">Conversation Summary</h2>
                <p className="text-blue-100">
                  {formatDate(new Date(summary.conversation_date))}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:text-gray-200 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <Clock className="w-8 h-8 text-blue-500 mx-auto mb-2" />
              <div className="text-2xl font-bold text-blue-600">
                {summary.duration_minutes || 'N/A'}
              </div>
              <div className="text-sm text-blue-700">Minutes</div>
            </div>
            <div className="bg-green-50 rounded-lg p-4 text-center">
              <Calendar className="w-8 h-8 text-green-500 mx-auto mb-2" />
              <div className="text-2xl font-bold text-green-600">
                {summary.appointments_discussed?.length || 0}
              </div>
              <div className="text-sm text-green-700">Appointments</div>
            </div>
            <div className="bg-purple-50 rounded-lg p-4 text-center">
              <User className="w-8 h-8 text-purple-500 mx-auto mb-2" />
              <div className="text-2xl font-bold text-purple-600">
                {summary.user_preferences?.length || 0}
              </div>
              <div className="text-sm text-purple-700">Preferences</div>
            </div>
          </div>

          {summary.appointments_discussed && summary.appointments_discussed.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
                <Calendar className="w-5 h-5 mr-2 text-green-500" />
                Appointments Discussed
              </h3>
              <div className="space-y-3">
                {summary.appointments_discussed.map((appointment, index) => (
                  <div key={index} className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <CheckCircle className="w-5 h-5 text-green-500" />
                        <div>
                          <div className="font-medium text-gray-800">
                            {appointment.purpose || 'General Consultation'}
                          </div>
                          <div className="text-sm text-gray-600">
                            {appointment.date} at {appointment.time}
                          </div>
                        </div>
                      </div>
                      <div className="text-xs text-green-600 bg-green-100 px-2 py-1 rounded">
                        {appointment.status || 'Booked'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {summary.user_preferences && summary.user_preferences.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
                <User className="w-5 h-5 mr-2 text-purple-500" />
                User Preferences
              </h3>
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <div className="flex flex-wrap gap-2">
                  {summary.user_preferences.map((preference, index) => (
                    <span
                      key={index}
                      className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm"
                    >
                      {preference}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
              <MessageSquare className="w-5 h-5 mr-2 text-blue-500" />
              Conversation Summary
            </h3>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-gray-800 leading-relaxed">
                {summary.summary_text}
              </p>
            </div>
          </div>

          {summary.user_phone && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">Contact Information</h3>
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <User className="w-4 h-4 text-gray-500" />
                  <span className="text-gray-800">Phone: {summary.user_phone}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="bg-gray-50 px-6 py-4 flex items-center justify-between border-t">
          <div className="text-sm text-gray-500">
            Generated on {formatDate(new Date())}
          </div>
          <div className="flex space-x-3">
            <button
              onClick={handleShare}
              className="flex items-center space-x-2 px-4 py-2 text-blue-600 hover:text-blue-700 transition-colors"
            >
              <Share className="w-4 h-4" />
              <span>Share</span>
            </button>
            <button
              onClick={handleDownload}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
            >
              <Download className="w-4 h-4" />
              <span>Download</span>
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConversationSummary;
