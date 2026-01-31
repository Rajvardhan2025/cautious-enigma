# Voice Appointment Assistant - Frontend

A React-based voice appointment booking system with LiveKit integration.

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── AvatarDisplay.tsx
│   │   ├── ConnectionStatus.tsx
│   │   ├── ConversationSummary.tsx
│   │   ├── ToolCallDisplay.tsx
│   │   ├── VoiceAgentInterface.tsx
│   │   └── VoiceInterface.tsx
│   ├── pages/              # Page components with routing
│   │   ├── HomePage.tsx    # Landing page with session setup
│   │   └── SessionPage.tsx # Active voice session page
│   ├── config/             # Configuration and constants
│   │   ├── env.ts          # Environment variables configuration
│   │   ├── constants.ts    # Application constants
│   │   ├── index.ts        # Config exports
│   │   └── README.md       # Configuration guide
│   ├── types/              # TypeScript type definitions
│   │   └── index.ts
│   ├── lib/                # Utility functions
│   │   ├── api.ts          # API client functions
│   │   └── utils.ts        # General utilities
│   ├── App.tsx             # Main app with routing setup
│   ├── main.tsx            # Application entry point
│   ├── vite-env.d.ts       # TypeScript environment declarations
│   └── index.css           # Global styles
├── public/                 # Static assets
├── .env                    # Environment variables
├── .env.example            # Environment variables template
└── package.json
```

## Architecture Highlights

### Centralized Configuration
All environment variables are managed in `src/config/env.ts`. This provides:
- Single source of truth for all env variables
- Type-safe configuration access
- Built-in validation
- Easy testing and mocking

### API Layer
API calls are abstracted in `src/lib/api.ts` for:
- Consistent error handling
- Reusable request logic
- Easy to test and mock
- Type-safe responses

### Constants Management
Application constants in `src/config/constants.ts` for:
- No magic strings/numbers in code
- Easy to update values
- Better maintainability
- Type-safe constants

## Features

- Natural voice conversation with AI assistant
- Real-time appointment booking
- Visual avatar display
- Activity tracking and tool call display
- Conversation summaries
- LiveKit integration for voice communication

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Configure environment variables in `.env`:
```env
VITE_LIVEKIT_TOKEN_URL=http://localhost:8000/api/token
```

3. Start the development server:
```bash
npm run dev
```

## Routes

- `/` - Home page with session setup
- `/session` - Active voice session with the AI assistant

## Technology Stack

- React 18
- TypeScript
- React Router v6
- LiveKit Components
- Tailwind CSS
- Vite

## Environment Variables

All environment variables are centralized in `src/config/env.ts` for easy management.

- `VITE_LIVEKIT_TOKEN_URL` - Backend API endpoint for LiveKit token generation (LiveKit URL is provided by the backend)
- `VITE_BEYOND_PRESENCE_API_KEY` - Optional: Beyond Presence API key for avatar
- `VITE_TAVUS_API_KEY` - Optional: Tavus API key for avatar
- `VITE_APP_NAME` - Application name
- `VITE_APP_VERSION` - Application version

### Using Configuration

Import the config in your components:

```typescript
import config from '@/config/env';

// Access environment variables
const tokenUrl = config.livekit.tokenUrl;
const appName = config.app.name;
```

Import constants:

```typescript
import { ROUTES, APP_CONSTANTS, FEATURES } from '@/config/constants';

// Use constants
navigate(ROUTES.HOME);
console.log(APP_CONSTANTS.STATUS.CONNECTED);
```
