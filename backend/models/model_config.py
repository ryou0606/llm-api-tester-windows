"""模型配置表 - 存储用户配置的 LLM 模型信息"""

from datetime import datetime, timezone
from sqlalchemy import Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ModelConfig(Base):
    """模型配置 ORM 模型"""

    __tablename__ = "model_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="用户自定义名称")
    api_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="API 格式类型: openai_compat / anthropic / gemini / wenxin / tongyi"
    )
    base_url: Mapped[str] = mapped_column(String(512), nullable=False, comment="API Base URL")
    api_key: Mapped[str] = mapped_column(Text, nullable=False, comment="API Key")
    model_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="模型 ID")
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="上下文窗口大小")
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="最大输出 token")
    supports_vision: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否支持图片理解")
    supports_audio: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否支持语音")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    # 状态字段：记录最后一次测试结果
    status: Mapped[str] = mapped_column(
        String(20), default="untested",
        comment="模型状态: untested / available / unavailable"
    )
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最后测试时间")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), comment="更新时间"
    )
