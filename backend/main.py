"""
FastAPI 应用入口

初始化应用，挂载路由，配置 CORS，启动数据库。
"""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from database import init_db, AsyncSessionLocal
from known_models import seed_known_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await init_db()
    # 初始化已知模型数据
    async with AsyncSessionLocal() as session:
        await seed_known_models(session)
    print("✅ 数据库初始化完成")
    yield
    # 关闭时清理资源
    print("👋 应用关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="LLM API Tester",
    description="大模型 API 测试与对比工具",
    version="0.1.0",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载前端静态文件
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

# 挂载路由
from routers.models import router as models_router  # noqa: E402
from routers.chat import router as chat_router  # noqa: E402
from routers.arena import router as arena_router  # noqa: E402
from routers.audio import router as audio_router  # noqa: E402
from routers.relay import router as relay_router  # noqa: E402

app.include_router(models_router)
app.include_router(chat_router)
app.include_router(arena_router)
app.include_router(audio_router)
app.include_router(relay_router)


@app.get("/api/health", tags=["系统"])
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "version": "0.1.0",
        "supported_api_types": [
            "openai_compat", "anthropic", "gemini", "wenxin", "tongyi"
        ],
    }


@app.get("/", tags=["前端"])
async def root():
    """前端入口"""
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "LLM API Tester API — 前端未构建，请访问 /docs 查看 API 文档"}


@app.get("/vite.svg", tags=["前端"])
async def vite_svg():
    svg_path = os.path.join("static", "vite.svg")
    if os.path.exists(svg_path):
        return FileResponse(svg_path)
    return {"message": "Not found"}


@app.get("/{path:path}", tags=["前端"])
async def spa_fallback(path: str):
    """SPA 回退：非 API 路由返回 index.html"""
    # 排除 API 和静态文件路径
    if path.startswith("api/") or path.startswith("assets/"):
        return {"detail": "Not Found"}
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Not Found"}
