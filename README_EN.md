# LLM API Tester

[中文](./README.md) | English

A comprehensive LLM API testing and comparison tool with a modern Web UI.

## ✨ Features

- 🤖 **Single Model Test** - Connectivity, response, latency, token usage with streaming support
- ⚔️ **Multi-Model Arena** - Send the same prompt to multiple models and compare outputs side by side
- 👁 **Vision Test** - Upload images + text questions to test model vision capabilities
- 🎤 **Audio Interaction** - STT speech recognition + TTS speech synthesis (MiMo priority)
- 🔌 **Relay Station** - Expose OpenAI-compatible API for other agents to call
- 📋 **Smart Paste** - Paste any format text, auto-recognize model configurations (supports 22+ providers)
- 🔄 **Remote Model Fetching** - Auto-fetch available model lists from API
- 🌐 **i18n Support** - Chinese and English interface

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12+ / FastAPI / SQLAlchemy / httpx |
| Frontend | Vue 3 / Vite / Element Plus / Pinia / TypeScript |
| Database | SQLite (aiosqlite) |
| Container | Docker / docker-compose |

## 🚀 Quick Start

### Option 1: Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Frontend dev server runs at http://localhost:5173, API requests are proxied to backend port 8000.

### Option 2: Docker Deployment

```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

Backend API runs at http://localhost:8000.

### Option 3: Production Deployment

```bash
# Build frontend
cd frontend
npm run build

# Start backend (frontend dist hosted by nginx or other web server)
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## 📁 Project Structure

```
llm-api-tester/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Global configuration
│   ├── database.py          # Database connection
│   ├── known_models.py      # Known model context window data (80+ models)
│   ├── adapters/            # API adapters
│   │   ├── base.py          # Adapter base class
│   │   ├── openai_compat.py # OpenAI compatible adapter
│   │   └── registry.py      # Adapter registry
│   ├── routers/             # API routes
│   │   ├── models.py        # Model CRUD
│   │   ├── chat.py          # Single model chat
│   │   ├── arena.py         # Multi-model arena
│   │   ├── audio.py         # Audio STT/TTS
│   │   └── relay.py         # Relay station (/v1/)
│   └── services/            # Business logic
├── frontend/
│   └── src/
│       ├── views/           # 6 pages
│       ├── stores/          # Pinia state management
│       ├── api/             # API call wrappers
│       └── components/      # Common components
├── Dockerfile
└── docker-compose.yml
```

## 📡 API Endpoints

### Internal API (/api/)

| Endpoint | Description |
|----------|-------------|
| `GET/POST /api/models` | Model configuration CRUD |
| `POST /api/models/{id}/test` | Test model connection |
| `POST /api/models/parse` | Smart paste parsing |
| `POST /api/models/fetch-remote-models` | Fetch remote model list |
| `GET /api/models/providers` | Search provider suggestions |
| `POST /api/chat/send` | Single model chat |
| `POST /api/chat/stream` | Single model streaming chat |
| `POST /api/arena/send` | Multi-model arena |
| `POST /api/arena/stream` | Multi-model streaming arena |
| `POST /api/audio/stt` | Speech to text |
| `POST /api/audio/tts` | Text to speech |

### Relay Station API (/v1/)

Exposes OpenAI-compatible endpoints for other agents:

```bash
# List available models
curl http://localhost:8000/v1/models

# Chat completion
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_TESTER_HOST` | `0.0.0.0` | Listen address |
| `LLM_TESTER_PORT` | `8000` | Listen port |
| `LLM_TESTER_DEBUG` | `false` | Debug mode |

### Data Directory

SQLite database is stored in `backend/data/` directory. Docker deployment uses volume mount for persistence.

## 🤖 Supported Models

Built-in context window data for 80+ models, auto-filled when adding models:

MiMo / OpenAI / Anthropic / DeepSeek / Gemini / GLM / Qwen / Moonshot / Baichuan / MiniMax / Yi / Step / Groq / SiliconFlow / OpenRouter / Fireworks

## 📄 License

MIT
