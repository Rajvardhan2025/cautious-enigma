/**
 * Application Constants
 * Non-environment specific constants used throughout the application
 */

export const APP_CONSTANTS = {
  // Room name generation
  ROOM_PREFIX: 'voice-agent',
  USER_PREFIX: 'user',
  
  // Connection timeouts
  CONNECTION_TIMEOUT: 30000, // 30 seconds
  AGENT_WAIT_DELAY: 2000, // 2 seconds
  
  // UI Constants
  MAX_TRANSCRIPT_ITEMS: 100,
  ACTIVITY_PANEL_WIDTH: 384, // 96 * 4 (w-96 in Tailwind)
  
  // Agent identification
  AGENT_IDENTITY_KEYWORDS: ['agent', 'voice'],
  
  // Status messages
  STATUS: {
    CONNECTING: 'Connecting to voice session...',
    CONNECTED: 'Connected',
    DISCONNECTED: 'Disconnected',
    ERROR: 'Connection Error',
  },
} as const;

export const ROUTES = {
  HOME: '/',
  SESSION: '/session',
} as const;

export const FEATURES = [
  'Natural voice conversation',
  'Real-time appointment booking',
  'Visual avatar display',
  'Conversation summaries',
] as const;
