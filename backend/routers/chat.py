"""
对话路由 - 提供对话创建、消息发送、历史查询等接口

支持普通请求和流式 SSE 两种模式。
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.chat_service import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["对话"])


# ============ Pydantic 请求/响应模型 ============

class CreateConversationRequest(BaseModel):
    """创建对话请求"""
    model_config_id: int = Field(..., description="模型配置 ID")
    title: str | None = Field(None, description="对话标题")


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    conversation_id: int = Field(..., description="对话 ID")
    model_config_id: int = Field(..., description="模型配置 ID")
    content: str = Field(..., min_length=1, description="消息内容")
    image_data: str | None = Field(None, description="Base64 图片数据（可选）")
    temperature: float | None = Field(None, ge=0, le=2, description="温度参数")
    max_tokens: int | None = Field(None, ge=1, description="最大输出 token")


class ConversationResponse(BaseModel):
    """对话响应"""
    id: int
    title: str | None
    mode: str
    model_config_ids: str | None
    created_at: str


class MessageResponse(BaseModel):
    """消息响应"""
    content: str
    model: str
    usage: dict
    latency_ms: int
    raw_response: dict
    finish_reason: str


class MessageHistoryItem(BaseModel):
    """历史消息条目"""
    id: int
    role: str
    content: str | None
    image_data: str | None
    token_usage: str | None
    latency_ms: int | None
    raw_response: str | None
    created_at: str


# ============ 接口 ============

@router.post("/create", summary="创建新对话")
async def create_conversation(
    data: CreateConversationRequest,
    db: AsyncSession = Depends(get_db),
):
    """创建新的对话会话"""
    try:
        conversation = await chat_service.create_conversation(
            db=db,
            model_config_id=data.model_config_id,
            title=data.title,
        )
        return {
            "id": conversation.id,
            "title": conversation.title,
            "mode": conversation.mode,
            "model_config_ids": conversation.model_config_ids,
            "created_at": conversation.created_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"创建对话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建对话失败: {str(e)}")


@router.get("/list", summary="获取对话列表")
async def list_conversations(
    mode: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """获取所有对话列表"""
    conversations = await chat_service.list_conversations(db, mode=mode)
    return [
        {
            "id": c.id,
            "title": c.title,
            "mode": c.mode,
            "model_config_ids": c.model_config_ids,
            "created_at": c.created_at.isoformat(),
        }
        for c in conversations
    ]


@router.get("/history/{conversation_id}", summary="获取对话历史")
async def get_history(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取指定对话的所有消息"""
    conversation = await chat_service.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    messages = await chat_service.get_messages(db, conversation_id)
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "image_data": m.image_data,
            "token_usage": m.token_usage,
            "latency_ms": m.latency_ms,
            "raw_response": m.raw_response,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.post("/send", summary="发送消息（非流式）")
async def send_message(
    data: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    发送消息并获取模型回复

    返回完整的模型响应，包括内容、延迟、token 用量等。
    """
    # 验证对话存在
    conversation = await chat_service.get_conversation(db, data.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    try:
        response = await chat_service.send_message(
            db=db,
            conversation_id=data.conversation_id,
            model_config_id=data.model_config_id,
            content=data.content,
            image_data=data.image_data,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
        )
        return {
            "content": response.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            "latency_ms": response.latency_ms,
            "raw_response": response.raw_response,
            "finish_reason": response.finish_reason,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")


@router.post("/stream", summary="发送消息（流式 SSE）")
async def send_message_stream(
    data: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    发送消息并以 SSE 流式返回模型回复

    每个 SSE 事件格式：
    data: {"content": "增量文本", "finish_reason": null}

    结束事件：
    data: [DONE]
    """
    # 验证对话存在
    conversation = await chat_service.get_conversation(db, data.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    async def event_generator():
        """SSE 事件生成器"""
        try:
            async for chunk in chat_service.send_message_stream(
                db=db,
                conversation_id=data.conversation_id,
                model_config_id=data.model_config_id,
                content=data.content,
                image_data=data.image_data,
                temperature=data.temperature,
                max_tokens=data.max_tokens,
            ):
                event_data = json.dumps(
                    {"content": chunk.content, "finish_reason": chunk.finish_reason},
                    ensure_ascii=False,
                )
                yield f"data: {event_data}\n\n"

            # 发送结束标记
            yield "data: [DONE]\n\n"
        except ValueError as e:
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
        except Exception as e:
            logger.error(f"流式发送消息失败: {e}")
            error_data = json.dumps(
                {"error": f"请求失败: {str(e)}"}, ensure_ascii=False
            )
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )


@router.delete("/{conversation_id}", summary="删除对话")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除指定对话及其所有消息"""
    success = await chat_service.delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {"message": "删除成功"}
