"""测试记录表 - 记录模型测试的历史和结果"""

from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class TestRecord(Base):
    """测试记录 ORM 模型"""

    __tablename__ = "test_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_config_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("model_configs.id"), nullable=False, comment="测试的模型配置 ID"
    )
    test_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="测试类型: chat / vision / stt / tts"
    )
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True, comment="测试 prompt")
    response: Mapped[str | None] = mapped_column(Text, nullable=True, comment="模型响应")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="响应延迟(ms)")
    token_usage: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Token 用量 JSON")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="测试状态: success / error"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )
