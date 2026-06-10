"""
SQLite 数据库连接 & SQLAlchemy ORM 初始化
使用 aiosqlite 实现异步数据库操作
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import settings


# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},  # SQLite 需要此参数
)

# 创建异步 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


async def init_db():
    """初始化数据库，创建所有表"""
    # 导入所有模型以确保它们被注册到 Base.metadata
    from models.model_config import ModelConfig  # noqa: F401
    from models.conversation import Conversation  # noqa: F401
    from models.message import Message  # noqa: F401
    from models.test_record import TestRecord  # noqa: F401
    from models.tts_record import TTSRecord  # noqa: F401
    from models.known_model import KnownModel  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI 依赖注入：获取数据库 Session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
