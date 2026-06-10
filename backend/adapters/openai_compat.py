"""
OpenAI 兼容适配器

覆盖大部分主流模型厂商（OpenAI、DeepSeek、Moonshot、智谱、
百川、MiniMax、零一万物、阶跃星辰、SiliconFlow、Together AI、
Groq、Fireworks、OpenRouter 等），它们都使用相同的 API 格式。
"""

import time
import json
import httpx
from typing import AsyncIterator

from adapters.base import BaseModelAdapter, ChatResponse, ChatChunk, TokenUsage


# 请求超时配置（秒）
REQUEST_TIMEOUT = 60.0
STREAM_TIMEOUT = 120.0


class OpenAICompatAdapter(BaseModelAdapter):
    """OpenAI 兼容格式适配器"""

    async def chat(
        self,
        messages: list[dict],
        model_id: str,
        base_url: str,
        api_key: str,
        **kwargs
    ) -> ChatResponse:
        """发送普通对话请求"""
        url = f"{base_url.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_id,
            "messages": messages,
            "stream": False,
        }

        # 透传额外参数
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]

        start_time = time.monotonic()

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=payload)
            latency_ms = int((time.monotonic() - start_time) * 1000)

            response.raise_for_status()
            data = response.json()

        # 解析响应
        content = ""
        if data.get("choices"):
            choice = data["choices"][0]
            message = choice.get("message", {})
            content = message.get("content", "")

        # 解析 token 用量
        usage_data = data.get("usage", {})
        usage = TokenUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        finish_reason = "stop"
        if data.get("choices"):
            finish_reason = data["choices"][0].get("finish_reason", "stop")

        return ChatResponse(
            content=content,
            model=data.get("model", model_id),
            usage=usage,
            latency_ms=latency_ms,
            raw_response=data,
            finish_reason=finish_reason,
        )

    async def chat_stream(
        self,
        messages: list[dict],
        model_id: str,
        base_url: str,
        api_key: str,
        **kwargs
    ) -> AsyncIterator[ChatChunk]:
        """流式对话请求（SSE）"""
        url = f"{base_url.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_id,
            "messages": messages,
            "stream": True,
        }

        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]

        async with httpx.AsyncClient(timeout=STREAM_TIMEOUT) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()

                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if not line or line == "data: [DONE]":
                            continue
                        if line.startswith("data: "):
                            json_str = line[6:]
                            try:
                                data = json.loads(json_str)
                                if data.get("choices"):
                                    delta = data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    finish_reason = data["choices"][0].get("finish_reason")
                                    if content or finish_reason:
                                        yield ChatChunk(
                                            content=content,
                                            finish_reason=finish_reason,
                                        )
                            except json.JSONDecodeError:
                                continue

    async def vision(
        self,
        messages: list[dict],
        model_id: str,
        base_url: str,
        api_key: str,
        **kwargs
    ) -> ChatResponse:
        """
        图片理解 - 使用 OpenAI 兼容的多模态消息格式

        messages 中的 content 可以是数组格式：
        [
            {"type": "text", "text": "描述这张图片"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
        ]
        """
        # 直接复用 chat()，因为 OpenAI 兼容格式本身就支持多模态
        return await self.chat(messages, model_id, base_url, api_key, **kwargs)
