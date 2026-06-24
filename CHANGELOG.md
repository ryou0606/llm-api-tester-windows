# LLM API Tester - 修复记录

**日期**: 2026-06-10
**版本**: v1.1.0

## 新功能

### 🗣️ 多模型圆桌

新增"多模型圆桌"页面，支持多个 LLM 模型围绕一个话题自由讨论，互相可见对方发言并进行回应。

- 多模型并行发言，先完成先显示
- 用户控制每轮节奏：阅读完毕后手动结束本轮
- 每轮结束后可追加发言（补充信息、追问、引导方向）
- 可配置上下文轮数（默认6轮），控制每个模型可见的历史范围
- Token 默认不限制，可选配置
- 支持思考模式控制（DeepSeek 等模型）
- 圆桌历史自动保存，可在历史存档中查看

### 📋 提示词模板系统

新增全局提示词模板管理，圆桌讨论和多模型聊天室共用。

- 预置 2 个默认模板：批判性思维者、观点整合者
- 用户可新建/编辑/删除自定义模板
- 预置模板不可修改/删除
- 参与者配置时下拉选择模板自动填充，或手动输入

---

**日期**: 2026-06-10
**修复版本**: v1.0.1

## 修复的问题

### 🔴 P0 - 核心功能修复

#### 1. `send_chat()` / `send_chat_stream()` URL 双 `/v1` 问题
- **文件**: `app/services/llm_client.py`
- **问题**: `send_chat()` 固定拼接 `/v1/chat/completions`，当用户 base_url 已含 `/v1` 时导致双 `/v1` → 404
- **修复**: 新增 `_build_chat_url()` 统一函数，检测 `/v1` 后缀，与 `fetch_models()` 策略一致

#### 2. 批量测速 SSE 事件类型不匹配
- **文件**: `static/index.html`
- **问题**: 后端发 `start`/`progress`/`complete`，前端监听 `progress`/`result`/`done` → 测速结果永远不显示
- **修复**: 前端 SSE handler 改为处理 `start`、`progress`、`complete` 事件

#### 3. 多模型聊天室 SSE 事件类型不匹配
- **文件**: `static/index.html`
- **问题**: 后端发 `bot_start`/`bot_done`/`bot_error`/`all_done`，前端监听 `chunk`/`done`/`error` → 聊天室完全无法使用
- **修复**: 前端 SSE handler 改为匹配后端实际事件类型

### 🟠 P1 - 逻辑缺陷修复

#### 4. 测速历史记录自动保存
- **文件**: `static/index.html`
- **问题**: 测速完成后从未调用 save API，历史记录丢失
- **修复**: 在 `complete` 事件处理中自动调用 `POST /api/speed-test/save`

#### 5. 聊天室 bot_id 匹配
- **文件**: `static/index.html`
- **问题**: 前端用 `model` 作 key 匹配 bot 消息，后端用 `bot_id` → 无法对应
- **修复**: `createChatroom()` 存储后端返回的 `bot_id`，`sendMessage()` 用 `bot_id` 作 key

#### 6. 聊天室 bot 字段名标准化
- **文件**: `static/index.html`
- **问题**: 后端返回 `nickname`，前端期望 `nick` → 显示异常
- **修复**: `createChatroom()` 中标准化 `nickname` → `nick`

#### 7. 历史记录 XSS 风险
- **文件**: `static/index.html`
- **问题**: `rerunSpeedTest()` 用 `JSON.stringify(r)` 拼入 onclick 属性，prompt 中特殊字符可导致 XSS
- **修复**: 改用 `state._historyRecords[idx]` 索引引用

### 🟡 P2 - 改进项

#### 8. `loadConfigs()` 返回值处理
- **文件**: `static/index.html`
- **问题**: `data.configs || data || []` 碰巧能工作但逻辑不清晰
- **修复**: 改为 `Array.isArray(data) ? data : (data.configs || [])`

#### 9. `exportBackup()` 对齐
- **文件**: `static/index.html`
- **问题**: 前端只导出配置，不导出历史
- **修复**: 改为调用后端 `/api/export/backup` 端点导出全量数据

#### 10. `exportHistory()` 逻辑清理
- **文件**: `static/index.html`
- **问题**: `data.records || data || []` 逻辑冗余
- **修复**: 直接用 `records` 变量

## 修改文件清单

| 文件 | 修改类型 |
|------|---------|
| `app/services/llm_client.py` | 新增 `_build_chat_url()`, 修改 `send_chat()`, `send_chat_stream()` |
| `static/index.html` | 修改 `renderModelGrid()`, `startSpeedTest()`, `createChatroom()`, `sendMessage()`, `loadHistory()`, `loadConfigs()`, `exportBackup()`, `exportHistory()` |

## 测试验证

- [x] 配置 CRUD (GET/POST/PUT/DELETE /api/configs)
- [x] 模型列表获取 (GET /api/combos)
- [x] 测速请求格式 (POST /api/speed-test, config_ids + model_map)
- [x] 测速 SSE 事件 (start → progress → complete)
- [x] 聊天室创建 (POST /chatroom/create, configId:model 解析)
- [x] 聊天室 SSE 事件 (bot_start → bot_done/bot_error → all_done)
- [x] 历史记录端点 (GET/DELETE /api/history)
- [x] 导出端点 (GET /api/export/backup)
- [x] 前端 JS 语法检查通过
