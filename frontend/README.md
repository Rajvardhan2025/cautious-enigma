# Voice Agent Frontend

React frontend for the voice appointment booking system using LiveKit Components.

## Tech Stack

- **React 19** with Vite
- **TypeScript** for type safety
- **LiveKit Components React** for voice/video
- **Tailwind CSS v3** for styling
- **Lucide React** for icons
- **Date-fns** for date formatting

## Setup

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your configuration
   ```

3. **Required Environment Variables**
   ```env
   VITE_LIVEKIT_URL=wss://your-livekit-server.livekit.cloud
   VITE_LIVEKIT_TOKEN_URL=http://localhost:8000/api/token
   ```

## Development

```bash
# Start development server
npm run dev

# Build for production (includes TypeScript compilation)
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint

# Type check
npx tsc --noEmit
```

## Components

### Core Components

- **App.jsx**: Main application with LiveKit room management
- **VoiceInterface**: Voice status and audio visualization
- **AvatarDisplay**: Avatar placeholder with state animations
- **ToolCallDisplay**: Real-time tool call visualization
- **ConversationSummary**: End-of-call summary modal
- **ConnectionStatus**: LiveKit connection status indicator

### Component Features

#### VoiceInterface
- Audio level visualization
- Microphone/speaker status
- Real-time transcript display
- Voice activity indicators

#### AvatarDisplay
- State-based animations (idle, listening, speaking)
- Placeholder for avatar integration
- Visual feedback for connection status

#### ToolCallDisplay
- Real-time tool call updates
- Expandable call details
- Status indicators (success/error/pending)
- Tool call statistics

#### ConversationSummary
- Appointment summaries
- User preferences tracking
- Download/share functionality
- Detailed conversation metrics

## Avatar Integration

The system is designed to integrate with avatar providers:

### Beyond Presence Integration
```javascript
// Example integration (to be implemented)
import { BeyondPresenceAvatar } from '@beyond-presence/react';

<BeyondPresenceAvatar
  apiKey={process.env.VITE_BEYOND_PRESENCE_API_KEY}
  avatarId="your-avatar-id"
  isListening={isListening}
  isSpeaking={isSpeaking}
/>
```

### Tavus Integration
```javascript
// Example integration (to be implemented)
import { TavusAvatar } from '@tavus/react';

<TavusAvatar
  apiKey={process.env.VITE_TAVUS_API_KEY}
  conversationId="conversation-id"
  onSpeechStart={() => setIsSpeaking(true)}
  onSpeechEnd={() => setIsSpeaking(false)}
/>
```

## LiveKit Integration

The app uses LiveKit Components for:

- **Room Management**: Automatic connection/disconnection
- **Audio Handling**: Real-time audio streaming
- **Participant Management**: Agent detection and status
- **Data Channels**: Tool call communication

### Key LiveKit Hooks Used

- `useRoomContext()`: Access to room instance
- `useConnectionState()`: Connection status monitoring
- `useParticipants()`: Participant list management
- `useTracks()`: Audio track monitoring
- `useLocalParticipant()`: Local user management

## Deployment

### Development
```bash
npm run dev
```

### Production Build
```bash
npm run build
npm run preview
```

### Environment Variables for Production
- Set `VITE_LIVEKIT_URL` to your LiveKit server
- Set `VITE_LIVEKIT_TOKEN_URL` to your token endpoint
- Configure avatar provider keys if using avatars

## Troubleshooting

### Common Issues

1. **LiveKit Connection Failed**
   - Check `VITE_LIVEKIT_URL` is correct
   - Verify token endpoint is accessible
   - Ensure CORS is configured on backend

2. **Audio Not Working**
   - Check browser permissions for microphone
   - Verify HTTPS connection (required for WebRTC)
   - Check audio device availability

3. **Tool Calls Not Displaying**
   - Verify data channel communication
   - Check agent is sending proper JSON format
   - Monitor browser console for errors

### Debug Mode

Enable debug logging:
```javascript
// In App.jsx
const room = useRoomContext();
room.setLogLevel('debug');
```

## Performance Optimization

- Components use React.memo for re-render optimization
- Audio visualizations use requestAnimationFrame
- Tool call updates are debounced
- Large conversation summaries are virtualized