"""
适配器基类 - 定义所有模型适配器的统一接口

所有 API 格式的适配器都继承自 BaseModelAdapter，
确保对外提供一致的调用方式和响应格式。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class TokenUsage:
    """Token 用量统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatResponse:
    """统一的对话响应格式"""
    content: str                    # 模型输出文本
    model: str                      # 实际使用的模型 ID
    usage: TokenUsage               # Token 用量
    latency_ms: int                 # 响应延迟（毫秒）
    raw_response: dict              # 原始 API 响应 JSON
    finish_reason: str = "stop"     # 结束原因: stop / length / error


@dataclass
class ChatChunk:
    """流式对话的单个数据块"""
    content: str                    # 本次增量文本
    finish_reason: str | None = None  # 结束原因（仅最后一个 chunk 有值）


class BaseModelAdapter(ABC):
    """
    模型适配器基类

    每种 API 格式（OpenAI 兼容、Anthropic、Gemini 等）
    实现一个子类，统一对外接口。

    子类必须实现:
        - chat(): 普通对话
        - chat_stream(): 流式对话
    可选实现:
        - vision(): 图片理解
        - stt(): 语音识别
        - tts(): 语音合成
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        model_id: str,
        base_url: str,
        api_key: str,
        **kwargs
    ) -> ChatResponse:
        """
        发送对话请求，获取完整响应

        Args:
            messages: 对话消息列表 [{"role": "user", "content": "..."}]
            model_id: 模型 ID
            base_url: API Base URL
            api_key: API Key
            **kwargs: 其他参数（temperature, max_tokens 等）

        Returns:
            ChatResponse: 统一格式的响应
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        model_id: str,
        base_url: str,
        api_key: str,
        **kwargs
    ) -> AsyncIterator[ChatChunk]:
        """
        流式对话请求

        Args:
            messages: 对话消息列表
            model_id: 模型 ID
            base_url: API Base URL
            api_key: API Key
            **kwargs: 其他参数

        Yields:
            ChatChunk: 增量文本数据块
        """
        pass

    async def vision(
        self,
        messages: list[dict],
        model_id: str,
        base_url: str,
        api_key: str,
        **kwargs
    ) -> ChatResponse:
        """
        图片理解（可选实现）

        默认回退到 chat()，子类可覆盖以支持多模态输入。
        """
        return await self.chat(messages, model_id, base_url, api_key, **kwargs)

    async def stt(
        self,
        audio_data: str,
        model_id: str,
        base_url: str,
        api_key: str,
        **kwargs
    ) -> str:
        """
        语音识别（可选实现）

        Args:
            audio_data: Base64 编码的音频数据

        Returns:
            str: 识别出的文字
        """
        raise NotImplementedError(f"{self.__class__.__name__} 不支持 STT")

    async def tts(
        self,
        text: str,
        voice: str,
        model_id: str,
        base_url: str,
        api_key: str,
        **kwargs
    ) -> bytes:
        """
        语音合成（可选实现）

        Args:
            text: 要合成的文本
            voice: 音色 ID

        Returns:
            bytes: 音频数据
        """
        raise NotImplementedError(f"{self.__class__.__name__} 不支持 TTS")

    async def test_connection(
        self,
        model_id: str,
        base_url: str,
        api_key: str,
    ) -> ChatResponse:
        """
        测试连接 - 发送一个简单请求验证 API 配置是否正确

        默认发送 "Hi" 作为测试消息。
        """
        return await self.chat(
            messages=[{"role": "user", "content": "Hi"}],
            model_id=model_id,
            base_url=base_url,
            api_key=api_key,
            max_tokens=10,
        )
