<div align="center">

# 🧪 LLM API Tester

**All-in-One OpenAI-Compatible API Testing Platform — Benchmark · Chat · Roundtable Discussion**

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/ryou0606/llm-api-tester?style=social)](https://github.com/ryou0606/llm-api-tester)

<br/>

A lightweight, zero-database LLM API testing tool with batch benchmarking, multi-model chatroom, and multi-model roundtable discussion.<br/>
Compatible with all OpenAI-format APIs — OpenAI, DeepSeek, Claude (relay), Gemini (relay), Ollama, LM Studio, vLLM, and more.

<br/>

![Single File](https://img.shields.io/badge/Single_File_Deploy-Ready_to_Use-ff6b6b?style=for-the-badge)
![No DB](https://img.shields.io/badge/No_Database-JSON_Storage-4ecdc4?style=for-the-badge)
![Windows](https://img.shields.io/badge/EXE_Packaging-One_Click-6c5ce7?style=for-the-badge)

</div>

---

## 📸 Feature Preview

<table>
<tr>
<td width="50%">

### 🗣️ Multi-Model Roundtable
![Roundtable Config](screenshots/多模型圆桌功能1.png)
![Roundtable Discussion](screenshots/多模型圆桌2.png)

</td>
<td width="50%">

### 💬 Multi-Model Chatroom
![Multi-Model Chat](screenshots/多模型聊天（所有选中的模型参与%20会对用户的内容回复%20不会读取其他模型的内容）.png)

</td>
</tr>
</table>

> 💡 **Most Unique Feature:** Let multiple AI models freely discuss a topic — they can see each other's responses and reply accordingly. Enable "Auto Mode" and the AI models will automatically proceed through multiple rounds while you simply observe.

---

## ✨ Feature Highlights

<table>
<tr>
<td width="50%">

### 🏎️ Batch API Benchmarking
- Concurrent multi-config benchmarking with TTFB / throughput / latency comparison
- Custom Prompt, System Prompt, Temperature, Top_P
- Real-time SSE streaming results — fastest finishes first
- Auto-saved benchmark history with Excel export
- Independent reasoning model thinking time stats

</td>
<td width="50%">

### 💬 Multi-Model Chatroom
- Chat with multiple LLMs simultaneously, compare response quality in real-time
- Each bot has independent nickname, persona, color, and system prompt
- Reasoning model thinking process display
- Streaming output with character-by-character rendering
- Configurable context rounds

</td>
</tr>
<tr>
<td>

### 🗣️ Multi-Model Roundtable Discussion
- Multiple AIs freely discuss the same topic
- Cross-visible responses with mutual references
- Hidden user identity support (models can't distinguish human from AI)
- Auto Mode: automatically proceed to next round when current round ends
- Each participant has independent system prompt + 13 preset persona templates

</td>
<td>

### 📋 Prompt Template System
- 13 carefully designed preset templates (Critical Thinker, Devil's Advocate, Philosopher, etc.)
- Custom template CRUD, shared between chatroom and roundtable
- Dropdown selection with auto-fill, manual editing supported
- Preset templates are protected from modification/deletion

</td>
</tr>
</table>

### 🔧 More Features

| Feature | Description |
|---------|-------------|
| 🔌 Wide Compatibility | Supports all OpenAI-format APIs: OpenAI, DeepSeek, Claude/Gemini relay, Ollama, LM Studio, vLLM, One API, etc. |
| 🤖 Auto Model Discovery | One-click fetch of all available models from API endpoint, compatible with multiple response formats |
| 🧠 Reasoning Model Support | DeepSeek-R1, QwQ and other chain-of-thought models with independent reasoning process display |
| 📊 Excel Export | One-click export of benchmark results to formatted `.xlsx` files |
| 💾 Full Backup | One-click export/import of all configurations and history |
| 🌙 Dark Theme | Eye-friendly dark UI for extended use |
| 🖥️ Windows EXE | PyInstaller packaging support for single-file executable |
| 📡 Proxy Support | Each API configuration can have its own HTTP proxy |
| ⚡ Zero Database | JSON file storage, no database installation required |
| 🔒 Local Deployment | All data stays local, no third-party services involved |

---

## 🚀 Quick Start

### Option 1: Run from Source (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/ryou0606/llm-api-tester.git
cd llm-api-tester

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start
python main.py
```

Browser will automatically open `http://localhost:12390` (port auto-discovery).

### Option 2: Windows EXE

```bash
# Windows users: double-click build.bat to package
build.bat

# After packaging, run
dist\LLM-API-Tester\LLM-API-Tester.exe
```

### Option 3: Manual Start

```bash
# Start on specified port
uvicorn app.server:app --host 0.0.0.0 --port 8080

# Then open in browser
open http://localhost:8080
```

---

## 📸 Detailed Features

### 1️⃣ API Configuration Management

Add your LLM API endpoints with support for:

- **Base URL**: e.g., `https://api.openai.com/v1`, `http://localhost:11434/v1`
- **API Key**: Leave empty for local models (Ollama, etc.)
- **Model Discovery**: Click "Fetch Models" to auto-retrieve available model list
- **Connection Test**: One-click endpoint reachability verification
- **Proxy Settings**: Independent HTTP proxy per configuration

```
Supported API Formats:
├── OpenAI Standard Format (/{base}/v1/chat/completions)
├── URLs with /v1 (auto-deduplication)
├── Ollama (http://localhost:11434/v1)
├── LM Studio (http://localhost:1234/v1)
├── vLLM / Text Generation Inference
├── One API / New API relays
└── Any OpenAI Chat Completions compatible service
```

### 2️⃣ Batch API Benchmarking

Select multiple model configurations, set benchmark parameters, and start with one click:

- **Concurrency Control**: 1-20 concurrent requests for stress testing
- **Multi-round Testing**: 1-50 rounds to eliminate random误差
- **Core Metrics**:
  - ⏱ **TTFB** (Time to First Byte) — Perceived response speed
  - ⚡ **Throughput** (tokens/s) — Generation speed
  - 🕐 **Total Time** — End-to-end completion time
  - 📊 **Standard Deviation** — Stability assessment
  - 💭 **Thinking Time** — Independent stats for reasoning models
- **Real-time Streaming**: SSE live updates, fastest finishes first
- **History Records**: Auto-saved, supports retrospective comparison
- **Excel Export**: Formatted spreadsheet download with one click

### 3️⃣ Multi-Model Chatroom

Chat with multiple AI models simultaneously, compare response quality horizontally:

- Each bot can be configured with independent nickname, persona, color, and system prompt
- All bots receive user messages simultaneously and reply in parallel
- Reasoning model thinking process display (collapsible)
- Real-time streaming output with character-by-character rendering
- Message clearing, exit chatroom, and other operations

### 4️⃣ Multi-Model Roundtable Discussion 🗣️

> **This is the most unique feature of this project.**

Let multiple AI models freely discuss a topic — they can see each other's responses and reply accordingly.

**Core Features:**

- **Cross-Visible**: Each participant can see others' responses, forming a real discussion
- **Parallel Speaking**: All participants start simultaneously, fastest finishes first
- **Round Control**: In manual mode, user clicks "End Round" after reading to proceed to next round
- **Auto Mode**: Automatically proceeds to next round when current round ends, ideal for observation
- **Additional Input**: Append user messages after each round to guide discussion direction
- **Hidden Identity**: When enabled, models cannot distinguish user messages from AI messages

**Participant Configuration:**

Each participant can be independently configured with:
- 🏷️ **Nickname**: Randomly assigned or custom
- 🎭 **Persona**: Role positioning (default: random)
- 🎨 **Color**: Bubble color differentiation
- 📝 **System Prompt**: Independent system-level instructions
- 📋 **Prompt Template**: 13 preset templates with one-click fill

**Preset Prompt Templates:**

| Template | Description |
|----------|-------------|
| 🔍 Critical Thinker | Examine logic chains, find loopholes and counterexamples |
| 🧩 Perspective Integrator | Find connections and consensus between conflicting viewpoints |
| 🌈 Creative Free Spirit | Cross-domain associations, propose crazy but valuable ideas |
| ✂️ Concise Pragmatist | Extremely concise, straight to the essence, no more than three sentences |
| 📖 Storyteller | Express viewpoints through stories and cases |
| 😈 Devil's Advocate | Deliberately stand on the opposite side, stress-test mainstream views |
| 🌀 Philosophical Speculator | Question essence, challenge premise assumptions |
| 😄 Light-hearted Humorist | Use humor to ease tense atmosphere |
| 📊 Data-Driven Analyst | Support viewpoints with facts and data |
| 🚀 Action-Oriented | Convert discussions into concrete action items |
| 🗡️ Sharp Critic | Hit the nail on the head, no mercy |
| 🌧️ Pessimist | Calmly remind of various risks and worst-case scenarios |
| 🧊 Cold Observer | Objective analysis, point out emotional biases |

### 5️⃣ History & Export

- **Benchmark History**: Each benchmark result auto-saved, up to 200 records
- **Roundtable History**: Auto-saved after roundtable discussion ends, up to 100 records
- **Excel Export**: Export benchmark results to formatted `.xlsx` with header styles and auto column width
- **Full Backup**: One-click export of all configurations and history as JSON file
- **Backup Restore**: Import JSON backup file to restore data

---

## 🏗️ Project Structure

```
llm-api-tester/
├── main.py                          # Entry point: port discovery, browser launch, uvicorn start
├── requirements.txt                 # Python dependencies
├── build.bat                        # Windows one-click packaging script
├── llm_tester.spec                  # PyInstaller configuration
├── CHANGELOG.md                     # Changelog
│
├── app/
│   ├── __init__.py
│   ├── server.py                    # FastAPI app definition, static file mounting, export endpoints
│   ├── models.py                    # Pydantic data models
│   │
│   ├── routes/
│   │   ├── configs.py               # API config CRUD + model discovery + connection test
│   │   ├── speed.py                 # Benchmark SSE + history saving + Excel export
│   │   ├── chatroom.py              # Chatroom creation + message sending SSE
│   │   ├── roundtable.py            # Roundtable creation + round control + user messages
│   │   ├── history.py               # History CRUD
│   │   └── prompt_templates.py      # Prompt template CRUD (13 presets included)
│   │
│   └── services/
│       ├── llm_client.py            # Async HTTP client (httpx), compatible with multiple API formats
│       ├── chat_manager.py          # Chatroom lifecycle management
│       ├── roundtable_manager.py    # Roundtable lifecycle management
│       ├── speed_tester.py          # Concurrent benchmark engine
│       └── data_store.py            # JSON file storage layer
│
├── static/
│   └── index.html                   # Single-page frontend (HTML + CSS + JS, no framework dependency)
│
└── data/                            # Runtime data directory (auto-created)
    ├── api_configs.json             # API configurations
    ├── speed_history.json           # Benchmark history
    ├── roundtable_history.json      # Roundtable history
    └── prompt_templates.json        # User custom templates
```

---

## 🔌 API Documentation

### API Configuration

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/configs` | Get all configurations |
| `POST` | `/api/configs` | Create configuration |
| `PUT` | `/api/configs/{id}` | Update configuration |
| `DELETE` | `/api/configs/{id}` | Delete configuration |
| `POST` | `/api/configs/check` | Check all configurations connectivity |
| `GET` | `/api/combos` | Get model list for enabled configurations |
| `POST` | `/api/fetch-models` | Fetch available models from endpoint |
| `POST` | `/api/test-connection` | Test connection |

### Benchmarking

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/speed-test` | Run benchmark (SSE streaming) |
| `POST` | `/api/speed-test/save` | Save benchmark results |
| `GET` | `/api/export/speed-excel` | Export benchmark history as Excel |

### Chatroom

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chatroom/create` | Create chatroom |
| `POST` | `/api/chatroom/message` | Send message (SSE streaming) |
| `POST` | `/api/chatroom/{id}/stop` | Stop chatroom |
| `POST` | `/api/chatroom/{id}/clear` | Clear messages |
| `GET` | `/api/chatroom/{id}/history` | Get chat history |

### Roundtable Discussion

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/roundtable/create` | Create roundtable |
| `POST` | `/api/roundtable/{id}/next-round` | Start next round (SSE streaming) |
| `POST` | `/api/roundtable/{id}/end-round` | End current round |
| `POST` | `/api/roundtable/{id}/message` | Append user message |
| `POST` | `/api/roundtable/{id}/stop` | Stop roundtable and save |
| `POST` | `/api/roundtable/{id}/clear` | Clear messages |
| `GET` | `/api/roundtable/{id}/history` | Get roundtable history |

### History & Templates

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/history?type=speed\|roundtable` | Get history records |
| `DELETE` | `/api/history/{id}?type=...` | Delete single record |
| `DELETE` | `/api/history?type=...` | Clear all history of specified type |
| `GET` | `/api/prompt-templates` | Get all templates |
| `POST` | `/api/prompt-templates` | Create template |
| `PUT` | `/api/prompt-templates/{id}` | Update template |
| `DELETE` | `/api/prompt-templates/{id}` | Delete template |

### Data Export

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/export/all` | Export all data (JSON) |
| `GET` | `/api/export/backup` | Download full backup file |

### SSE Event Format

Benchmarking and chat/roundtable use Server-Sent Events for streaming:

```
# Benchmark Events
data: {"type":"start","config_name":"...","model":"..."}
data: {"type":"progress","config_name":"...","model":"...","round":1,"ttfb":0.5,"speed":45.2,...}
data: {"type":"complete","config_name":"...","model":"...","results":[...]}

# Roundtable Events
data: {"type":"round_start","round":1}
data: {"type":"participant_start","participant_id":"...","nick":"..."}
data: {"type":"participant_done","participant_id":"...","content":"...","ttfb":0.8,...}
data: {"type":"round_done","round":1}
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_TESTER_DATA_DIR` | Data storage directory | `./data` |
| `LLM_TESTER_STATIC_DIR` | Static files directory | `./static` |

### Dependencies

```
fastapi>=0.104.0          # Web framework
uvicorn[standard]>=0.24.0 # ASGI server
httpx>=0.25.0             # Async HTTP client
openpyxl>=3.1.0           # Excel export
psutil>=5.9.0             # System info
pydantic>=2.0.0           # Data validation
python-multipart>=0.0.6   # File upload support
```

---

## 🛠️ Development Guide

### Local Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Start development server (auto hot-reload)
uvicorn app.server:app --reload --port 12390

# Frontend changes take effect on browser refresh (no build step required)
```

### Package as Windows EXE

```bash
# Option 1: Run packaging script
build.bat

# Option 2: Manual packaging
pip install pyinstaller
pyinstaller llm_tester.spec --noconfirm --clean
# After packaging, copy static/ directory to dist/LLM-API-Tester/static/
```

Packaged output is in `dist/LLM-API-Tester/` directory — double-click `LLM-API-Tester.exe` to run.

### Adding New Features

```
1. Data Models    → app/models.py         (Define request/response models)
2. Business Logic → app/services/          (Core service layer)
3. API Routes     → app/routes/            (FastAPI routes)
4. Frontend UI    → static/index.html      (Single-file SPA)
5. Register Route → app/server.py          (include_router)
```

---

## 🤝 Compatibility

Tested and verified on the following platforms:

| Service/Platform | Status | Notes |
|------------------|--------|-------|
| OpenAI API | ✅ | GPT-4o, GPT-4-turbo, etc. |
| DeepSeek | ✅ | With reasoning model R1 chain-of-thought display |
| Ollama | ✅ | Local models, no API key required |
| LM Studio | ✅ | Local models |
| vLLM | ✅ | Self-deployed models |
| One API | ✅ | Multi-model relay |
| New API | ✅ | Multi-model relay |
| Cloudflare Workers AI | ✅ | OpenAI-format compatible gateway |
| Any OpenAI-Compatible API | ✅ | As long as it supports `/v1/chat/completions` |

---

## 📄 License

MIT License — Free to use, modify, and distribute.

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.io/) — High-performance Python web framework
- [httpx](https://www.python-httpx.org/) — Modern async HTTP client
- [openpyxl](https://openpyxl.readthedocs.io/) — Excel file processing
- [uvicorn](https://www.uvicorn.org/) — Lightweight ASGI server

---

<div align="center">

**If this project helps you, please give it a ⭐ Star!**

<br/>

[![Star History Chart](https://api.star-history.com/svg?repos=ryou0606/llm-api-tester&type=Date)](https://star-history.com/#ryou0606/llm-api-tester&Date)

</div>
