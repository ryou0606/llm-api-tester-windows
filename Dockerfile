# LLM API Tester - 多阶段构建 Dockerfile
# 第一阶段：编译前端，第二阶段：运行后端

# 第一阶段：构建前端
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend

# 复制前端代码
COPY frontend/package*.json ./
COPY frontend/tsconfig.json ./
COPY frontend/vite.config.ts ./
COPY frontend/index.html ./
COPY frontend/env.d.ts ./
COPY frontend/src ./src
COPY frontend/public ./public

# 安装依赖并构建
RUN npm ci && npm run build

# 第二阶段：运行后端
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ .

# 复制前端构建产物到 static 目录
COPY --from=frontend-builder /app/frontend/dist ./static

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# 启动服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
