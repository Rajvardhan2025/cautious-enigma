import React from 'react';
import { 
  Calendar, 
  User, 
  MessageSquare, 
  Download,
} from 'lucide-react';
import { formatDate } from '../lib/utils';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from './ui/dialog';

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
  open: boolean;
  onClose: () => void;
}

const ConversationSummary: React.FC<ConversationSummaryProps> = ({ summary, open, onClose }) => {
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
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden p-0 border-0 w-[95vw] sm:w-full">
        <div className="border-b border-gray-200 px-4 sm:px-6 py-4 sm:py-5">
          <DialogHeader>
            <DialogTitle className="text-lg sm:text-xl font-medium text-gray-900">
              Conversation Summary
            </DialogTitle>
            <DialogDescription className="text-xs sm:text-sm text-gray-500 mt-1">
              {formatDate(new Date(summary.conversation_date))}
            </DialogDescription>
          </DialogHeader>
        </div>

        <div className="px-4 sm:px-6 py-3 sm:py-4 overflow-y-auto max-h-[calc(90vh-200px)] space-y-4 sm:space-y-6">

          {summary.appointments_discussed && summary.appointments_discussed.length > 0 && (
            <div>
              <h3 className="text-xs sm:text-sm font-medium text-gray-900 mb-2 sm:mb-3 flex items-center gap-2">
                <Calendar className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-400" />
                Appointments
              </h3>
              <div className="space-y-2">
                {summary.appointments_discussed.map((appointment, index) => (
                  <div key={index} className="border border-gray-200 rounded-md p-2.5 sm:p-3 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start justify-between gap-2 sm:gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="text-xs sm:text-sm font-medium text-gray-900 truncate">
                          {appointment.purpose || 'General Consultation'}
                        </div>
                        <div className="text-[10px] sm:text-xs text-gray-500 mt-1">
                          {appointment.date} · {appointment.time}
                        </div>
                      </div>
                      {appointment.status && (
                        <span className="text-[10px] sm:text-xs text-gray-600 bg-gray-100 px-1.5 sm:px-2 py-0.5 sm:py-1 rounded whitespace-nowrap">
                          {appointment.status}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {summary.user_preferences && summary.user_preferences.length > 0 && (
            <div>
              <h3 className="text-xs sm:text-sm font-medium text-gray-900 mb-2 sm:mb-3 flex items-center gap-2">
                <User className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-400" />
                Preferences
              </h3>
              <div className="flex flex-wrap gap-1.5 sm:gap-2">
                {summary.user_preferences.map((preference, index) => (
                  <span
                    key={index}
                    className="text-[10px] sm:text-xs text-gray-700 bg-gray-100 px-2 sm:px-3 py-1 sm:py-1.5 rounded-full"
                  >
                    {preference}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div>
            <h3 className="text-xs sm:text-sm font-medium text-gray-900 mb-2 sm:mb-3 flex items-center gap-2">
              <MessageSquare className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-400" />
              Summary
            </h3>
            <div className="text-xs sm:text-sm text-gray-700 leading-relaxed">
              {summary.summary_text}
            </div>
          </div>

          {summary.user_phone && (
            <div>
              <h3 className="text-xs sm:text-sm font-medium text-gray-900 mb-2 sm:mb-3">Contact</h3>
              <div className="text-xs sm:text-sm text-gray-600">
                {summary.user_phone}
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="border-t border-gray-200 px-4 sm:px-6 py-3 sm:py-4">
          <div className="flex flex-col sm:flex-row items-center justify-between w-full gap-3 sm:gap-0">
            <div className="text-[10px] sm:text-xs text-gray-400 hidden sm:block">
              {formatDate(new Date())}
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <button
                onClick={handleDownload}
                className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                <Download className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                <span className="hidden sm:inline">Download</span>
                <span className="sm:hidden">Save</span>
              </button>
              <button
                onClick={onClose}
                className="flex-1 sm:flex-none px-3 sm:px-4 py-2 text-xs sm:text-sm font-medium text-white bg-gray-900 rounded-md hover:bg-gray-800 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ConversationSummary;
