/**
 * Environment Configuration
 * Centralized configuration for all environment variables
 */

interface AppConfig {
  // API Configuration
  api: {
    baseUrl: string;
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
  api: {
    baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
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
  
  if (!config.api.baseUrl) {
    errors.push('VITE_API_BASE_URL is required');
  }
  
  if (errors.length > 0) {
    // Only log in development mode
    if (import.meta.env.DEV) {
      console.warn('[Config] Running with incomplete configuration');
    }
  }
};

// Validate on load
validateConfig();

export default config;
