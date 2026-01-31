# Voice Appointment Agent - Backend

Backend server for the Voice Appointment Assistant, built with FastAPI and LiveKit Agents.

## Prerequisites (macOS)

Before starting, ensure you have the following installed:

- **Python 3.9+**: Check with `python3 --version`
  ```bash
  # Install via Homebrew if needed
  brew install python@3.11
  ```

- **MongoDB**: Required for storing appointment data
  ```bash
  # Install via Homebrew
  brew tap mongodb/brew
  brew install mongodb-community
  
  # Start MongoDB service
  brew services start mongodb-community
  ```

- **pip**: Python package manager (comes with Python)
  ```bash
  python3 -m pip --version
  ```

## Quick Start

### 1. Set Up Virtual Environment

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env.local
```

Edit `.env.local` with your credentials:

```bash
# Required API Keys
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
DEEPGRAM_API_KEY=your_deepgram_key

# Choose your LLM provider (gemini, cerebras, or openai)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key

# MongoDB (default local setup)
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=voice_agent
```

### 4. Verify Setup

Check that everything is configured correctly:

```bash
python3 start.py check
```

You should see:
```
✅ Environment variables configured
✅ Dependencies installed
✅ System ready!
```

## Running the Services

### Option 1: Run Everything (Recommended)

Start both the API server and LiveKit agent:

```bash
python3 start.py both
```

This will start:
- **API Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **LiveKit Agent**: Connected to LiveKit Cloud

### Option 2: Run Services Separately

**API Server Only:**
```bash
python3 start.py api
```

**LiveKit Agent Only:**
```bash
python3 start.py agent
```

**Agent with Different Modes:**
```bash
# Development mode (default)
python3 start.py agent --mode dev

# Console mode (for testing)
python3 start.py agent --mode console

# Production mode
python3 start.py agent --mode start
```

## Manual Service Commands

If you prefer to run services manually:

### API Server
```bash
# From backend directory
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### LiveKit Agent
```bash
# From backend directory
python3 -m agent.main dev
```

## Project Structure

```
backend/
├── agent/              # LiveKit agent implementation
│   ├── main.py        # Agent entry point
│   └── tools.py       # Agent tools and logic
├── api/               # FastAPI REST API
│   ├── main.py        # API entry point
│   ├── routers/       # API route handlers
│   └── schemas.py     # Pydantic models
├── core/              # Core functionality
│   ├── database.py    # MongoDB connection
│   └── models.py      # Data models
├── start.py           # Unified startup script
├── requirements.txt   # Python dependencies
└── .env.local        # Environment configuration
```

## API Endpoints

Once the API server is running, visit http://localhost:8000/docs for interactive API documentation.

Key endpoints:
- `GET /health` - Health check
- `POST /api/token` - Generate LiveKit connection token
- `GET /api/appointments` - List appointments
- `POST /api/appointments` - Create appointment

## Troubleshooting

### MongoDB Connection Issues

If you see MongoDB connection errors:

```bash
# Check if MongoDB is running
brew services list | grep mongodb

# Start MongoDB if not running
brew services start mongodb-community

# Check MongoDB logs
tail -f /opt/homebrew/var/log/mongodb/mongo.log
```

### Port Already in Use

If port 8000 is already in use:

```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
kill -9 $(lsof -ti:8000)
```

### Virtual Environment Issues

If you have issues with the virtual environment:

```bash
# Deactivate current environment
deactivate

# Remove and recreate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Missing API Keys

Ensure all required API keys are set in `.env.local`:
- LiveKit credentials (URL, API key, API secret)
- Deepgram API key (for speech-to-text)
- At least one LLM provider key (Gemini, Cerebras, or OpenAI)

### Agent Not Connecting

If the agent fails to connect to LiveKit:

1. Verify your LiveKit credentials in `.env.local`
2. Check that your LiveKit URL starts with `wss://`
3. Ensure your LiveKit project is active
4. Check agent logs for specific error messages

## Development Tips

### Logging Configuration

The application uses structured logging with different levels:
- **INFO**: Important events (user actions, tool calls, appointments)
- **WARNING**: Issues that don't stop execution
- **ERROR**: Failures and exceptions
- **DEBUG**: Detailed information (disabled by default)

To enable debug logging, set in `.env.local`:
```bash
LOG_LEVEL=DEBUG
```

Noisy third-party loggers (pymongo, livekit plugins) are automatically silenced to WARNING level.

### Hot Reload

Both services support hot reload:
- API server automatically reloads on file changes
- Agent requires restart for code changes

### Viewing Logs

The startup script shows logs from both services. For more detailed logging:

```bash
# Set log level in .env.local
LOG_LEVEL=DEBUG
```

### Testing the Agent

Use the LiveKit CLI to test agent functionality:

```bash
# Install LiveKit CLI
brew install livekit-cli

# Test agent connection
lk room create test-room
```

## Stopping Services

Press `Ctrl+C` to stop all running services. The script will gracefully shut down both the API server and agent.

## Production Deployment

For production deployment:

1. Set `ENVIRONMENT=production` in `.env.local`
2. Use a production MongoDB instance
3. Configure proper CORS origins in `api/main.py`
4. Use a process manager like systemd or supervisord
5. Set up proper logging and monitoring

## Getting Help

- Check the logs for error messages
- Run `python3 start.py check` to verify configuration
- Visit http://localhost:8000/docs for API documentation
- Review LiveKit documentation: https://docs.livekit.io/

## License

See LICENSE file in the root directory.
