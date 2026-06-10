"""
多模型对抗服务 - 并发调用多个模型，对比输出结果

核心逻辑：
1. 接收同一用户消息
2. 并发发送给所有已选模型
3. 收集各模型的响应（支持流式）
"""

import json
import asyncio
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


class ArenaService:
    """多模型对抗服务"""

    async def create_arena(
        self,
        db: AsyncSession,
        model_config_ids: list[int],
        title: str | None = None,
    ) -> Conversation:
        """
        创建对抗会话

        Args:
            db: 数据库会话
            model_config_ids: 参与对抗的模型配置 ID 列表
            title: 对话标题

        Returns:
            创建的对话对象
        """
        # 验证所有模型存在
        for mid in model_config_ids:
            result = await db.execute(select(ModelConfig).where(ModelConfig.id == mid))
            if not result.scalar_one_or_none():
                raise ValueError(f"模型配置 #{mid} 不存在")

        conversation = Conversation(
            title=title or f"对抗 ({len(model_config_ids)} 模型)",
            mode="arena",
            model_config_ids=json.dumps(model_config_ids),
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        logger.info(f"创建对抗会话 #{conversation.id}，模型: {model_config_ids}")
        return conversation

    async def list_arenas(self, db: AsyncSession) -> list[Conversation]:
        """获取所有对抗会话"""
        result = await db.execute(
            select(Conversation)
            .where(Conversation.mode == "arena")
            .order_by(Conversation.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_arena(self, db: AsyncSession, conversation_id: int) -> Conversation | None:
        """获取对抗会话详情"""
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.mode == "arena",
            )
        )
        return result.scalar_one_or_none()

    async def get_model_configs(
        self, db: AsyncSession, model_config_ids: list[int]
    ) -> list[ModelConfig]:
        """批量获取模型配置"""
        result = await db.execute(
            select(ModelConfig).where(ModelConfig.id.in_(model_config_ids))
        )
        return list(result.scalars().all())

    async def send_message(
        self,
        db: AsyncSession,
        conversation_id: int,
        model_config_ids: list[int],
        content: str,
    ) -> dict[int, ChatResponse]:
        """
        发送消息给所有模型（非流式），并发执行

        Returns:
            {model_config_id: ChatResponse} 映射
        """
        # 保存用户消息
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )
        db.add(user_message)
        await db.commit()

        # 获取模型配置
        configs = await self.get_model_configs(db, model_config_ids)
        config_map = {c.id: c for c in configs}

        # 构建历史消息
        messages = await self._build_messages(db, conversation_id)

        # 并发调用所有模型
        async def call_model(model_config_id: int) -> tuple[int, ChatResponse | Exception]:
            config = config_map.get(model_config_id)
            if not config:
                return model_config_id, ValueError(f"模型配置 #{model_config_id} 不存在")
            try:
                adapter = adapter_registry.get(config.api_type)
                response = await adapter.chat(
                    messages=messages,
                    model_id=config.model_id,
                    base_url=config.base_url,
                    api_key=config.api_key,
                )
                return model_config_id, response
            except Exception as e:
                logger.error(f"模型 {config.name} 调用失败: {e}")
                return model_config_id, e

        results = await asyncio.gather(
            *[call_model(mid) for mid in model_config_ids],
            return_exceptions=True,
        )

        # 保存结果
        responses: dict[int, ChatResponse] = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"并发调用异常: {result}")
                continue
            model_config_id, resp = result
            if isinstance(resp, Exception):
                # 保存错误消息
                error_msg = Message(
                    conversation_id=conversation_id,
                    model_config_id=model_config_id,
                    role="assistant",
                    content=f"[错误] {str(resp)}",
                )
                db.add(error_msg)
            else:
                responses[model_config_id] = resp
                # 保存助手消息
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    model_config_id=model_config_id,
                    role="assistant",
                    content=resp.content,
                    token_usage=json.dumps({
                        "prompt_tokens": resp.usage.prompt_tokens,
                        "completion_tokens": resp.usage.completion_tokens,
                        "total_tokens": resp.usage.total_tokens,
                    }),
                    latency_ms=resp.latency_ms,
                    raw_response=json.dumps(resp.raw_response, ensure_ascii=False),
                )
                db.add(assistant_msg)

        await db.commit()
        return responses

    async def send_message_stream(
        self,
        db: AsyncSession,
        conversation_id: int,
        model_config_ids: list[int],
        content: str,
    ) -> AsyncIterator[dict]:
        """
        发送消息给所有模型（流式），并发执行

        Yields:
            {"model_config_id": int, "content": str, "finish_reason": str|None}
            或 {"model_config_id": int, "error": str}
            最后 {"done": True}
        """
        # 保存用户消息
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )
        db.add(user_message)
        await db.commit()

        # 获取模型配置
        configs = await self.get_model_configs(db, model_config_ids)
        config_map = {c.id: c for c in configs}

        # 构建历史消息
        messages = await self._build_messages(db, conversation_id)

        # 每个模型的收集器
        collected: dict[int, list[str]] = {mid: [] for mid in model_config_ids}
        finished: set[int] = set()

        async def stream_model(model_config_id: int, queue: asyncio.Queue):
            config = config_map.get(model_config_id)
            if not config:
                await queue.put({"model_config_id": model_config_id, "error": f"模型配置 #{model_config_id} 不存在"})
                await queue.put({"model_config_id": model_config_id, "content": "", "finish_reason": "error"})
                return
            try:
                adapter = adapter_registry.get(config.api_type)
                async for chunk in adapter.chat_stream(
                    messages=messages,
                    model_id=config.model_id,
                    base_url=config.base_url,
                    api_key=config.api_key,
                ):
                    collected[model_config_id].append(chunk.content)
                    await queue.put({
                        "model_config_id": model_config_id,
                        "content": chunk.content,
                        "finish_reason": chunk.finish_reason,
                    })
            except Exception as e:
                logger.error(f"模型 {config.name} 流式调用失败: {e}")
                await queue.put({"model_config_id": model_config_id, "error": str(e)})
                await queue.put({"model_config_id": model_config_id, "content": "", "finish_reason": "error"})

        queue: asyncio.Queue = asyncio.Queue()

        # 启动所有模型的流式调用
        tasks = [
            asyncio.create_task(stream_model(mid, queue))
            for mid in model_config_ids
        ]

        # 等待所有任务完成的信号
        done_event = asyncio.Event()

        async def wait_all():
            await asyncio.gather(*tasks, return_exceptions=True)
            done_event.set()

        asyncio.create_task(wait_all())

        # 持续从队列中取出结果 yield
        while not done_event.is_set() or not queue.empty():
            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.1)
                mid = item.get("model_config_id")
                if "error" in item:
                    yield item
                elif item.get("finish_reason"):
                    finished.add(mid)
                    yield item
                else:
                    yield item
            except asyncio.TimeoutError:
                continue

        # 所有模型完成后，保存消息到数据库
        for mid in model_config_ids:
            full_content = "".join(collected[mid])
            if full_content:
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    model_config_id=mid,
                    role="assistant",
                    content=full_content,
                )
                db.add(assistant_msg)

        await db.commit()
        yield {"done": True}

    async def get_arena_history(
        self, db: AsyncSession, conversation_id: int
    ) -> dict[int, list[Message]]:
        """
        获取对抗会话的历史消息，按模型分组

        Returns:
            {model_config_id: [Message, ...]} 分组后的消息
        """
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        messages = list(result.scalars().all())

        grouped: dict[int, list[Message]] = {}
        for msg in messages:
            mid = msg.model_config_id or 0  # 0 表示用户消息
            if mid not in grouped:
                grouped[mid] = []
            grouped[mid].append(msg)

        return grouped

    async def delete_arena(self, db: AsyncSession, conversation_id: int) -> bool:
        """删除对抗会话及其消息"""
        conversation = await self.get_arena(db, conversation_id)
        if not conversation:
            return False

        # 删除关联消息
        result = await db.execute(
            select(Message).where(Message.conversation_id == conversation_id)
        )
        for msg in result.scalars().all():
            await db.delete(msg)

        await db.delete(conversation)
        await db.commit()
        return True

    async def _build_messages(self, db: AsyncSession, conversation_id: int) -> list[dict]:
        """构建发送给模型的消息列表"""
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        messages = []
        for msg in result.scalars().all():
            if msg.role == "user":
                messages.append({"role": "user", "content": msg.content or ""})
            elif msg.role == "assistant":
                messages.append({"role": "assistant", "content": msg.content or ""})
        return messages


# 全局单例
arena_service = ArenaService()
