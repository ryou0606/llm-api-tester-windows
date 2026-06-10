"""TTS 生成历史表 - 存储语音合成的历史记录"""

from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class TTSRecord(Base):
    """TTS 生成历史 ORM 模型"""

    __tablename__ = "tts_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="TTS 模型 ID: mimo-v2.5-tts / mimo-v2.5-tts-voicedesign / mimo-v2.5-tts-voiceclone"
    )
    voice: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="音色 ID")
    text: Mapped[str] = mapped_column(Text, nullable=False, comment="输入文本")
    style: Mapped[str | None] = mapped_column(Text, nullable=True, comment="风格指令")
    audio_data: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Base64 音频数据")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )
