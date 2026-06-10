"""
多模型对抗路由 - 提供对抗会话的创建、消息发送、历史查询等接口

支持普通请求和流式 SSE 两种模式。
SSE 格式：每个事件包含 model_config_id，前端按模型分别收集。
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.arena_service import arena_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/arena", tags=["多模型对抗"])


# ============ Pydantic 请求/响应模型 ============

class CreateArenaRequest(BaseModel):
    """创建对抗会话请求"""
    model_config_ids: list[int] = Field(..., min_length=2, description="参与对抗的模型配置 ID（至少 2 个）")
    title: str | None = Field(None, description="对话标题")


class SendArenaMessageRequest(BaseModel):
    """对抗消息发送请求"""
    conversation_id: int = Field(..., description="对抗会话 ID")
    model_config_ids: list[int] = Field(..., min_length=1, description="目标模型配置 ID")
    content: str = Field(..., min_length=1, description="消息内容")


# ============ 接口 ============

@router.post("/create", summary="创建对抗会话")
async def create_arena(
    data: CreateArenaRequest,
    db: AsyncSession = Depends(get_db),
):
    """创建新的多模型对抗会话"""
    try:
        conversation = await arena_service.create_arena(
            db=db,
            model_config_ids=data.model_config_ids,
            title=data.title,
        )
        return {
            "id": conversation.id,
            "title": conversation.title,
            "mode": conversation.mode,
            "model_config_ids": json.loads(conversation.model_config_ids),
            "created_at": conversation.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建对抗会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建对抗会话失败: {str(e)}")


@router.get("/list", summary="获取对抗会话列表")
async def list_arenas(db: AsyncSession = Depends(get_db)):
    """获取所有对抗会话"""
    conversations = await arena_service.list_arenas(db)
    return [
        {
            "id": c.id,
            "title": c.title,
            "mode": c.mode,
            "model_config_ids": json.loads(c.model_config_ids) if c.model_config_ids else [],
            "created_at": c.created_at.isoformat(),
        }
        for c in conversations
    ]


@router.get("/{conversation_id}", summary="获取对抗会话详情")
async def get_arena(conversation_id: int, db: AsyncSession = Depends(get_db)):
    """获取对抗会话详情及模型信息"""
    conversation = await arena_service.get_arena(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对抗会话不存在")

    model_ids = json.loads(conversation.model_config_ids) if conversation.model_config_ids else []
    configs = await arena_service.get_model_configs(db, model_ids)

    return {
        "id": conversation.id,
        "title": conversation.title,
        "mode": conversation.mode,
        "model_config_ids": model_ids,
        "models": [
            {
                "id": c.id,
                "name": c.name,
                "model_id": c.model_id,
                "api_type": c.api_type,
                "status": c.status,
            }
            for c in configs
        ],
        "created_at": conversation.created_at.isoformat(),
    }


@router.get("/{conversation_id}/history", summary="获取对抗历史（按模型分组）")
async def get_arena_history(conversation_id: int, db: AsyncSession = Depends(get_db)):
    """获取对抗会话的历史消息，按模型分组返回"""
    conversation = await arena_service.get_arena(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对抗会话不存在")

    grouped = await arena_service.get_arena_history(db, conversation_id)

    result = {}
    for mid, messages in grouped.items():
        result[str(mid)] = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "token_usage": m.token_usage,
                "latency_ms": m.latency_ms,
                "raw_response": m.raw_response,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]

    return result


@router.post("/send", summary="发送消息（非流式）")
async def send_arena_message(
    data: SendArenaMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    同一消息发给所有模型，返回各模型的响应

    响应格式：{model_config_id: {content, model, usage, latency_ms, ...}}
    """
    conversation = await arena_service.get_arena(db, data.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对抗会话不存在")

    try:
        responses = await arena_service.send_message(
            db=db,
            conversation_id=data.conversation_id,
            model_config_ids=data.model_config_ids,
            content=data.content,
        )

        result = {}
        for mid, resp in responses.items():
            result[str(mid)] = {
                "content": resp.content,
                "model": resp.model,
                "usage": {
                    "prompt_tokens": resp.usage.prompt_tokens,
                    "completion_tokens": resp.usage.completion_tokens,
                    "total_tokens": resp.usage.total_tokens,
                },
                "latency_ms": resp.latency_ms,
                "raw_response": resp.raw_response,
                "finish_reason": resp.finish_reason,
            }
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"对抗发送消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送失败: {str(e)}")


@router.post("/stream", summary="发送消息（流式 SSE）")
async def send_arena_message_stream(
    data: SendArenaMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    同一消息发给所有模型，以 SSE 流式返回各模型的响应

    SSE 事件格式：
    data: {"model_config_id": 1, "content": "增量文本", "finish_reason": null}
    data: {"model_config_id": 2, "content": "Hi", "finish_reason": null}
    data: {"model_config_id": 1, "content": "", "finish_reason": "stop"}
    data: [DONE]
    """
    conversation = await arena_service.get_arena(db, data.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对抗会话不存在")

    async def event_generator():
        try:
            async for item in arena_service.send_message_stream(
                db=db,
                conversation_id=data.conversation_id,
                model_config_ids=data.model_config_ids,
                content=data.content,
            ):
                if item.get("done"):
                    yield "data: [DONE]\n\n"
                else:
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"对抗流式发送失败: {e}")
            error_data = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/{conversation_id}", summary="删除对抗会话")
async def delete_arena(conversation_id: int, db: AsyncSession = Depends(get_db)):
    """删除对抗会话及其所有消息"""
    success = await arena_service.delete_arena(db, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="对抗会话不存在")
    return {"message": "删除成功"}
