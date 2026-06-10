"""
全局配置模块
使用 pydantic-settings 管理，支持环境变量覆盖
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置"""

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # 数据库配置
    # 数据文件存放在 backend/data/ 目录下
    DATA_DIR: str = str(Path(__file__).parent / "data")
    DB_NAME: str = "llm_tester.db"

    # CORS 配置
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]

    @property
    def DATABASE_URL(self) -> str:
        """SQLite 数据库连接 URL"""
        db_path = os.path.join(self.DATA_DIR, self.DB_NAME)
        return f"sqlite+aiosqlite:///{db_path}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """同步 SQLite 连接 URL（用于初始化）"""
        db_path = os.path.join(self.DATA_DIR, self.DB_NAME)
        return f"sqlite:///{db_path}"

    class Config:
        env_prefix = "LLM_TESTER_"
        case_sensitive = False


# 全局单例
settings = Settings()

# 确保 data 目录存在
os.makedirs(settings.DATA_DIR, exist_ok=True)
