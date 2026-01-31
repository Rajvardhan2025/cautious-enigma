/// <reference types="vite/client" />

interface ImportMetaEnv {
  // LiveKit Configuration
  readonly VITE_LIVEKIT_TOKEN_URL: string;
  
  // Avatar Configuration
  readonly VITE_BEYOND_PRESENCE_API_KEY?: string;
  readonly VITE_TAVUS_API_KEY?: string;
  
  // Application Configuration
  readonly VITE_APP_NAME?: string;
  readonly VITE_APP_VERSION?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
