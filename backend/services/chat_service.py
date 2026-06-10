"""
对话服务 - 处理对话创建、消息发送、历史查询等业务逻辑

负责协调适配器调用与数据库存储。
"""

import json
import logging
from typing import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.conversation import Conversation
from models.message import Message
from models.model_config import ModelConfig
from adapters.base import ChatResponse, ChatChunk
from adapters.registry import adapter_registry

logger = logging.getLogger(__name__)


class ChatService:
    """对话服务"""

    async def create_conversation(
        self,
        db: AsyncSession,
        model_config_id: int,
        mode: str = "single",
        title: str | None = None,
    ) -> Conversation:
        """
        创建新对话

        Args:
            db: 数据库会话
            model_config_id: 模型配置 ID
            mode: 对话模式 (single / arena)
            title: 对话标题（可选，默认用 "新对话"）

        Returns:
            创建的对话对象
        """
        conversation = Conversation(
            title=title or "新对话",
            mode=mode,
            model_config_ids=json.dumps([model_config_id]),
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        logger.info(f"创建对话 #{conversation.id}，模型配置 #{model_config_id}")
        return conversation

    async def get_conversation(
        self, db: AsyncSession, conversation_id: int
    ) -> Conversation | None:
        """获取对话详情"""
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def list_conversations(
        self, db: AsyncSession, mode: str | None = None
    ) -> list[Conversation]:
        """
        获取对话列表

        Args:
            db: 数据库会话
            mode: 按模式筛选 (single / arena)，None 返回全部

        Returns:
            对话列表（按创建时间倒序）
        """
        query = select(Conversation).order_by(Conversation.created_at.desc())
        if mode:
            query = query.where(Conversation.mode == mode)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def delete_conversation(
        self, db: AsyncSession, conversation_id: int
    ) -> bool:
        """
        删除对话及其所有消息

        Returns:
            是否成功删除
        """
        conversation = await self.get_conversation(db, conversation_id)
        if not conversation:
            return False

        # 先删除关联的消息
        messages_result = await db.execute(
            select(Message).where(Message.conversation_id == conversation_id)
        )
        for msg in messages_result.scalars().all():
            await db.delete(msg)

        await db.delete(conversation)
        await db.commit()
        logger.info(f"删除对话 #{conversation_id}")
        return True

    async def get_messages(
        self, db: AsyncSession, conversation_id: int
    ) -> list[Message]:
        """获取对话的所有消息（按时间正序）"""
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def send_message(
        self,
        db: AsyncSession,
        conversation_id: int,
        model_config_id: int,
        content: str,
        image_data: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        """
        发送消息并获取模型回复（非流式）

        流程：
        1. 保存用户消息到数据库
        2. 获取历史消息构建上下文
        3. 调用适配器获取回复
        4. 保存助手消息到数据库

        Args:
            db: 数据库会话
            conversation_id: 对话 ID
            model_config_id: 模型配置 ID
            content: 用户消息内容
            image_data: 可选的 Base64 图片数据
            temperature: 温度参数
            max_tokens: 最大输出 token

        Returns:
            ChatResponse: 模型回复
        """
        # 获取模型配置
        model_config = await self._get_model_config(db, model_config_id)
        if not model_config:
            raise ValueError(f"模型配置 #{model_config_id} 不存在")

        # 保存用户消息
        user_message = Message(
            conversation_id=conversation_id,
            model_config_id=model_config_id,
            role="user",
            content=content,
            image_data=image_data,
        )
        db.add(user_message)
        await db.commit()

        # 构建消息上下文（包含历史消息）
        messages = await self._build_messages(db, conversation_id, image_data)

        # 获取适配器
        adapter = adapter_registry.get(model_config.api_type)

        # 构建调用参数
        kwargs = {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        # 调用模型 API
        logger.info(
            f"发送消息到 {model_config.name} ({model_config.model_id})，"
            f"对话 #{conversation_id}"
        )
        response = await adapter.chat(
            messages=messages,
            model_id=model_config.model_id,
            base_url=model_config.base_url,
            api_key=model_config.api_key,
            **kwargs,
        )

        # 保存助手消息
        assistant_message = Message(
            conversation_id=conversation_id,
            model_config_id=model_config_id,
            role="assistant",
            content=response.content,
            token_usage=json.dumps({
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }),
            latency_ms=response.latency_ms,
            raw_response=json.dumps(response.raw_response, ensure_ascii=False),
        )
        db.add(assistant_message)
        await db.commit()

        logger.info(
            f"收到回复: {response.latency_ms}ms, "
            f"tokens: {response.usage.total_tokens}"
        )
        return response

    async def send_message_stream(
        self,
        db: AsyncSession,
        conversation_id: int,
        model_config_id: int,
        content: str,
        image_data: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[ChatChunk]:
        """
        发送消息并获取模型回复（流式）

        流程：
        1. 保存用户消息
        2. 流式调用适配器
        3. 收集完整回复后保存助手消息

        Yields:
            ChatChunk: 增量文本数据块
        """
        # 获取模型配置
        model_config = await self._get_model_config(db, model_config_id)
        if not model_config:
            raise ValueError(f"模型配置 #{model_config_id} 不存在")

        # 保存用户消息
        user_message = Message(
            conversation_id=conversation_id,
            model_config_id=model_config_id,
            role="user",
            content=content,
            image_data=image_data,
        )
        db.add(user_message)
        await db.commit()

        # 构建消息上下文
        messages = await self._build_messages(db, conversation_id, image_data)

        # 获取适配器
        adapter = adapter_registry.get(model_config.api_type)

        # 构建调用参数
        kwargs = {}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        # 流式调用
        logger.info(
            f"流式发送消息到 {model_config.name} ({model_config.model_id})，"
            f"对话 #{conversation_id}"
        )

        full_content = ""
        async for chunk in adapter.chat_stream(
            messages=messages,
            model_id=model_config.model_id,
            base_url=model_config.base_url,
            api_key=model_config.api_key,
            **kwargs,
        ):
            full_content += chunk.content
            yield chunk

        # 流式结束后保存助手消息
        assistant_message = Message(
            conversation_id=conversation_id,
            model_config_id=model_config_id,
            role="assistant",
            content=full_content,
        )
        db.add(assistant_message)
        await db.commit()
        logger.info(f"流式回复完成，共 {len(full_content)} 字符")

    async def _get_model_config(
        self, db: AsyncSession, model_config_id: int
    ) -> ModelConfig | None:
        """获取模型配置"""
        result = await db.execute(
            select(ModelConfig).where(ModelConfig.id == model_config_id)
        )
        return result.scalar_one_or_none()

    async def _build_messages(
        self,
        db: AsyncSession,
        conversation_id: int,
        current_image: str | None = None,
    ) -> list[dict]:
        """
        构建发送给模型的消息列表

        从数据库读取历史消息，转换为 API 格式。
        """
        history = await self.get_messages(db, conversation_id)
        messages = []

        for msg in history:
            if msg.role == "user" and msg.image_data:
                # 含图片的消息使用多模态格式
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": msg.content or ""},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{msg.image_data}"
                            },
                        },
                    ],
                })
            elif msg.role == "user":
                messages.append({"role": "user", "content": msg.content or ""})
            elif msg.role == "assistant":
                messages.append({"role": "assistant", "content": msg.content or ""})

        return messages


# 全局单例
chat_service = ChatService()
