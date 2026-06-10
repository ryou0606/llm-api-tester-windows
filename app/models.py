"""Pydantic data models for the LLM API Tester."""
from typing import Optional
from pydantic import BaseModel, Field


class APIConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    base_url: str = Field(..., min_length=1)
    api_key: str = Field(default="")
    enabled: bool = True
    models: list[str] = []
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=1, le=128000)
    timeout: int = Field(default=120, ge=5, le=600)
    proxy: Optional[str] = None


class APIConfigUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    enabled: Optional[bool] = None
    models: Optional[list[str]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[int] = None
    proxy: Optional[str] = None


class FetchModelsRequest(BaseModel):
    base_url: str
    api_key: str = ""
    timeout: int = 30
    proxy: Optional[str] = None


class TestConnectionRequest(BaseModel):
    base_url: str
    api_key: str = ""
    timeout: int = 15
    proxy: Optional[str] = None


class SpeedTestRequest(BaseModel):
    config_ids: list[str]
    model_map: dict[str, str] = {}  # config_id -> model name override
    prompt: str = "请用中文详细介绍你自己，至少200字。"
    system_prompt: str = "你是一个有帮助的AI助手。"
    rounds: int = Field(default=3, ge=1, le=50)
    concurrency: int = Field(default=3, ge=1, le=20)
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=1.0, ge=0, le=1)
    max_tokens: int = Field(default=2048, ge=1, le=128000)


class ChatroomStartRequest(BaseModel):
    config_ids: list[str]
    system_prompt: str = ""
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=1.0, ge=0, le=1)
    max_tokens: int = Field(default=2048, ge=1, le=128000)


class ChatroomSendRequest(BaseModel):
    message: str = Field(..., min_length=1)


# ========== Prompt Templates ==========

class PromptTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    content: str = Field(default="")


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None


# ========== Roundtable ==========

class ParticipantConfig(BaseModel):
    model: str
    nick: str = ""
    persona: str = ""
    color: str = ""
    system_prompt: str = ""


class RoundtableCreateRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    context_rounds: int = Field(default=6, ge=1, le=50)
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=1.0, ge=0, le=1)
    max_tokens: Optional[int] = None
    thinking_mode: Optional[str] = None
    hide_user_identity: bool = False  # 隐藏用户身份，让模型分不清人和AI
    participants: list[ParticipantConfig]


class RoundtableMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
