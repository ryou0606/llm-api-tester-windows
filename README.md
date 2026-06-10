# LLM API Tester

[English](./README_EN.md) | 中文

大模型 API 测试与对比工具，带 Web 前端。

## 功能

- 🤖 **单模型测试** - 连通性、返回值、延迟、Token 用量，支持流式输出
- ⚔️ **多模型对抗** - 同一问题发给多个模型，并排对比输出
- 👁 **图片视觉** - 上传图片 + 文字提问，测试模型视觉理解
- 🎤 **语音交互** - STT 语音识别 + TTS 语音合成（MiMo 优先）
- 🔌 **中转站** - 对外暴露 OpenAI 兼容接口，供其他 Agent 调用
- 📋 **智能粘贴** - 粘贴任意格式文本，自动识别模型配置（支持 22 家厂商）
- 🔄 **远程模型拉取** - 从 API 自动获取可用模型列表

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12+ / FastAPI / SQLAlchemy / httpx |
| 前端 | Vue 3 / Vite / Element Plus / Pinia / TypeScript |
| 数据库 | SQLite（aiosqlite） |
| 容器 | Docker / docker-compose |

## 快速开始

### 方式一：本地开发

**后端：**
```bash
cd backend
pip install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**前端：**
```bash
cd frontend
npm install
npm run dev
```

前端开发服务器运行在 http://localhost:5173，API 请求自动代理到后端 8000 端口。

### 方式二：Docker 部署

```bash
# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

后端 API 运行在 http://localhost:8000。

### 方式三：生产部署

```bash
# 构建前端
cd frontend
npm run build

# 启动后端（前端 dist 由 nginx 或其他 web 服务器托管）
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## 项目结构

```
llm-api-tester/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 全局配置
│   ├── database.py          # 数据库连接
│   ├── known_models.py      # 已知模型上下文窗口数据（80+ 模型）
│   ├── adapters/            # API 适配器
│   │   ├── base.py          # 适配器基类
│   │   ├── openai_compat.py # OpenAI 兼容适配器
│   │   └── registry.py      # 适配器注册中心
│   ├── routers/             # API 路由
│   │   ├── models.py        # 模型 CRUD
│   │   ├── chat.py          # 单模型对话
│   │   ├── arena.py         # 多模型对抗
│   │   ├── audio.py         # 语音 STT/TTS
│   │   └── relay.py         # 中转站（/v1/）
│   └── services/            # 业务逻辑
├── frontend/
│   └── src/
│       ├── views/           # 6 个页面
│       ├── stores/          # Pinia 状态管理
│       ├── api/             # API 调用封装
│       └── components/      # 通用组件
├── Dockerfile
└── docker-compose.yml
```

## API 接口

### 内部接口（/api/）

| 接口 | 说明 |
|---|---|
| `GET/POST /api/models` | 模型配置 CRUD |
| `POST /api/models/{id}/test` | 测试模型连接 |
| `POST /api/models/parse` | 智能粘贴解析 |
| `POST /api/models/fetch-remote-models` | 拉取远程模型列表 |
| `GET /api/models/providers` | 搜索提供商建议 |
| `POST /api/chat/send` | 单模型对话 |
| `POST /api/chat/stream` | 单模型流式对话 |
| `POST /api/arena/send` | 多模型对抗 |
| `POST /api/arena/stream` | 多模型流式对抗 |
| `POST /api/audio/stt` | 语音识别 |
| `POST /api/audio/tts` | 语音合成 |

### 中转站接口（/v1/）

对外暴露 OpenAI 兼容接口，其他 Agent 可直接调用：

```bash
# 列出可用模型
curl http://localhost:8000/v1/models

# 对话补全
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `LLM_TESTER_HOST` | `0.0.0.0` | 监听地址 |
| `LLM_TESTER_PORT` | `8000` | 监听端口 |
| `LLM_TESTER_DEBUG` | `false` | 调试模式 |

### 数据目录

SQLite 数据库存放在 `backend/data/` 目录下，Docker 部署通过 volume 挂载持久化。

## 已知模型支持

内置 80+ 模型的上下文窗口数据，添加模型时自动填充：

MiMo / OpenAI / Anthropic / DeepSeek / Gemini / 智谱 GLM / 通义千问 / Moonshot / 百川 / MiniMax / 零一万物 / 阶跃星辰 / Groq / SiliconFlow / OpenRouter / Fireworks

## 许可

MIT
