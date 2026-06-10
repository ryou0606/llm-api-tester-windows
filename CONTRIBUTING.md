# 贡献指南

感谢你对 LLM API Tester 的兴趣！以下是参与贡献的方式。

## 如何贡献

### 报告 Bug

1. 在 [Issues](https://github.com/YOUR_USERNAME/llm-api-tester/issues) 中搜索是否已有相同问题
2. 如果没有，创建一个新的 Issue，包含：
   - 问题描述
   - 复现步骤
   - 期望行为 vs 实际行为
   - 环境信息（Python 版本、操作系统、API 类型）
   - 截图或错误日志（如有）

### 提交功能建议

在 Issues 中使用 `feature` 标签提交建议，描述：
- 你想要的功能
- 使用场景
- 你期望的行为

### 提交代码

```bash
# 1. Fork 仓库
# 2. 创建功能分支
git checkout -b feature/amazing-feature

# 3. 提交更改
git commit -m "feat: add amazing feature"

# 4. 推送到远程
git push origin feature/amazing-feature

# 5. 创建 Pull Request
```

### Commit 规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
feat: 新功能
fix: 修复 Bug
docs: 文档更新
style: 代码格式（不影响逻辑）
refactor: 重构
perf: 性能优化
test: 测试
chore: 构建/工具链
```

## 开发环境

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/llm-api-tester.git
cd llm-api-tester

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器（自动热重载）
uvicorn app.server:app --reload --port 12390
```

### 项目约定

- **后端**：FastAPI + Pydantic，异步优先（httpx）
- **前端**：原生 HTML/CSS/JS，无框架依赖，单文件 SPA
- **存储**：JSON 文件，无需数据库
- **兼容性**：Python 3.10+，支持 Windows/macOS/Linux

### 代码风格

- Python：遵循 PEP 8，使用 type hints
- JavaScript：ES6+，使用 `const`/`let`，避免 `var`
- 注释：关键逻辑必须有注释，函数必须有 docstring

## License

提交代码即表示你同意将代码以 MIT License 发布。
