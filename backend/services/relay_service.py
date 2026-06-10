"""
中转站服务 - 对外暴露 OpenAI 兼容接口

其他 Agent（OpenClaw、Claude Code、脚本等）可通过本服务
调用已配置的模型，无需重复配置 API Key。
"""

import json
import logging
from typing import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.model_config import ModelConfig
from adapters.base import ChatResponse, ChatChunk
from adapters.registry import adapter_registry

logger = logging.getLogger(__name__)


class RelayService:
    """中转站服务"""

    async def list_models(self, db: AsyncSession) -> list[dict]:
        """
        获取所有可用模型列表（OpenAI /v1/models 格式）

        Returns:
            [{"id": "gpt-4o", "object": "model", "owned_by": "openai", ...}]
        """
        result = await db.execute(
            select(ModelConfig)
            .where(ModelConfig.is_active == True)
            .order_by(ModelConfig.name)
        )
        models = result.scalars().all()

        return [
            {
                "id": m.model_id,
                "object": "model",
                "created": int(m.created_at.timestamp()) if m.created_at else 0,
                "owned_by": self._extract_provider(m),
                "name": m.name,
                "relay_config_id": m.id,
            }
            for m in models
        ]

    async def chat_completions(
        self,
        db: AsyncSession,
        model_id: str,
        messages: list[dict],
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
    ) -> ChatResponse | AsyncIterator[ChatChunk]:
        """
        对话补全（OpenAI /v1/chat/completions 格式）

        根据 model_id 匹配已配置的模型，转发请求。

        Args:
            model_id: 模型 ID（精确匹配 model_config.model_id）
            messages: 消息列表
            stream: 是否流式
            temperature: 温度
            max_tokens: 最大 token
            top_p: top_p

        Returns:
            ChatResponse 或 AsyncIterator[ChatChunk]
        """
        # 查找匹配的模型配置
        config = await self._find_model(db, model_id)
        if not config:
            raise ValueError(f"模型 '{model_id}' 未配置或不可用")

        adapter = adapter_registry.get(config.api_type)

        kwargs = {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if top_p is not None:
            kwargs["top_p"] = top_p

        if stream:
            return adapter.chat_stream(
                messages=messages,
                model_id=config.model_id,
                base_url=config.base_url,
                api_key=config.api_key,
                **kwargs,
            )
        else:
            return await adapter.chat(
                messages=messages,
                model_id=config.model_id,
                base_url=config.base_url,
                api_key=config.api_key,
                **kwargs,
            )

    async def _find_model(self, db: AsyncSession, model_id: str) -> ModelConfig | None:
        """查找模型配置：精确匹配 model_id，优先可用的"""
        # 先找可用的
        result = await db.execute(
            select(ModelConfig).where(
                ModelConfig.model_id == model_id,
                ModelConfig.is_active == True,
                ModelConfig.status == "available",
            )
        )
        config = result.scalar_one_or_none()
        if config:
            return config

        # 退而求其次，找任意启用的
        result = await db.execute(
            select(ModelConfig).where(
                ModelConfig.model_id == model_id,
                ModelConfig.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    def _extract_provider(self, config: ModelConfig) -> str:
        """从 base_url 或 api_type 提取厂商名"""
        provider_map = {
            "openai": "openai",
            "deepseek": "deepseek",
            "moonshot": "moonshot",
            "zhipu": "zhipu",
            "baichuan": "baichuan",
            "minimax": "minimax",
            "01ai": "01.ai",
            "stepfun": "stepfun",
            "siliconflow": "siliconflow",
            "together": "together",
            "groq": "groq",
            "fireworks": "fireworks",
            "openrouter": "openrouter",
            "xiaomi": "xiaomi",
            "openai_compat": "custom",
        }
        return provider_map.get(config.api_type, config.api_type)


# 全局单例
relay_service = RelayService()
