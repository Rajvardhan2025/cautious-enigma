/**
 * Environment Configuration
 * Centralized configuration for all environment variables
 */

interface AppConfig {
  // LiveKit Configuration
  livekit: {
    tokenUrl: string;
  };
  
  // Avatar Configuration
  avatar: {
    beyondPresenceApiKey?: string;
    tavusApiKey?: string;
  };
  
  // Application Configuration
  app: {
    name: string;
    version: string;
  };
}

const config: AppConfig = {
  livekit: {
    tokenUrl: import.meta.env.VITE_LIVEKIT_TOKEN_URL || 'http://localhost:8000/api/token',
  },
  
  avatar: {
    beyondPresenceApiKey: import.meta.env.VITE_BEYOND_PRESENCE_API_KEY,
    tavusApiKey: import.meta.env.VITE_TAVUS_API_KEY,
  },
  
  app: {
    name: import.meta.env.VITE_APP_NAME || 'Voice Appointment Assistant',
    version: import.meta.env.VITE_APP_VERSION || '1.0.0',
  },
};

// Validate required environment variables
const validateConfig = () => {
  const errors: string[] = [];
  
  if (!config.livekit.tokenUrl) {
    errors.push('VITE_LIVEKIT_TOKEN_URL is required');
  }
  
  if (errors.length > 0) {
    console.error('Configuration errors:', errors);
    // Don't throw in production, just log warnings
    if (import.meta.env.DEV) {
      console.warn('Running with incomplete configuration in development mode');
    }
  }
};

// Validate on load
validateConfig();

export default config;
