export interface ToolCall {
  id: number;
  tool_name: string;
  parameters?: Record<string, any>;
  result: string;
  status: 'success' | 'error' | 'pending';
  timestamp: Date;
  type?: string;
}

export interface TranscriptItem {
  text: string;
  timestamp?: Date;
  speaker?: string;
  type?: string;
}

export interface ConversationSummaryData {
  conversation_date: string;
  duration_minutes?: number;
  appointments_discussed?: Array<{
    date: string;
    time: string;
    purpose?: string;
    status?: string;
  }>;
  user_preferences?: string[];
  summary_text: string;
  user_phone?: string;
}
