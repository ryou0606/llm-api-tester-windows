"""已知模型上下文窗口数据表 - 用于自动填充模型的上下文窗口大小"""

from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class KnownModel(Base):
    """已知模型上下文窗口 ORM 模型"""

    __tablename__ = "known_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True,
        comment="模型 ID（精确匹配）"
    )
    context_window: Mapped[int] = mapped_column(Integer, nullable=False, comment="上下文窗口大小（tokens）")
    provider: Mapped[str] = mapped_column(String(100), nullable=False, comment="厂商名称")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc), comment="更新时间"
    )
