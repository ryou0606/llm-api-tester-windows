"""对话历史表 - 存储单模型测试和多模型对抗的对话记录"""

from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Conversation(Base):
    """对话历史 ORM 模型"""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="对话标题")
    mode: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="对话模式: single / arena"
    )
    # 对抗模式下可能涉及多个模型，用 JSON 数组存储模型配置 ID
    model_config_ids: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="JSON 数组，对抗模式下多个模型配置 ID"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )
