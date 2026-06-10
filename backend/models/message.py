"""对话消息表 - 存储每条对话消息的详细信息"""

from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Message(Base):
    """对话消息 ORM 模型"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id"), nullable=False, comment="所属对话 ID"
    )
    model_config_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("model_configs.id"), nullable=True, comment="使用的模型配置 ID"
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="消息角色: user / assistant"
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="文字内容")
    image_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Base64 图片数据")
    audio_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Base64 音频数据")
    token_usage: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="JSON: {prompt_tokens, completion_tokens, total_tokens}"
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="响应延迟(ms)")
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原始响应 JSON")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )
