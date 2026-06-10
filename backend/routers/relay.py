"""
中转站路由 - 对外暴露 OpenAI 兼容接口

接口前缀 /v1/，与 OpenAI API 完全兼容。
外部 Agent 只需把 base_url 指向本项目即可使用。
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from services.relay_service import relay_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["中转站"])


# ============ Pydantic 请求模型 ============

class ChatMessage(BaseModel):
    role: str
    content: str | list | None = None


class ChatCompletionRequest(BaseModel):
    """OpenAI 兼容的对话补全请求"""
    model: str = Field(..., description="模型 ID")
    messages: list[ChatMessage] = Field(..., description="消息列表")
    stream: bool = Field(False, description="是否流式")
    temperature: float | None = Field(None, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=1)
    top_p: float | None = Field(None, ge=0, le=1)


# ============ 接口 ============

@router.get("/models", summary="列出可用模型")
async def list_models(db: AsyncSession = Depends(get_db)):
    """
    返回所有已配置且启用的模型（OpenAI /v1/models 格式）

    其他 Agent 调用 GET /v1/models 即可获取可用模型列表。
    """
    models = await relay_service.list_models(db)
    return {"object": "list", "data": models}


@router.post("/chat/completions", summary="对话补全")
async def chat_completions(
    data: ChatCompletionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    OpenAI 兼容的对话补全接口

    外部 Agent 调用 POST /v1/chat/completions 即可使用已配置的模型。
    支持普通和流式（SSE）两种模式。
    """
    # 转换消息格式
    messages = [{"role": m.role, "content": m.content or ""} for m in data.messages]

    try:
        if data.stream:
            # 流式模式
            async def event_generator():
                try:
                    chunk_iter = await relay_service.chat_completions(
                        db=db,
                        model_id=data.model,
                        messages=messages,
                        stream=True,
                        temperature=data.temperature,
                        max_tokens=data.max_tokens,
                        top_p=data.top_p,
                    )
                    async for chunk in chunk_iter:
                        chunk_data = {
                            "id": "chatcmpl-relay",
                            "object": "chat.completion.chunk",
                            "choices": [{
                                "index": 0,
                                "delta": {"content": chunk.content},
                                "finish_reason": chunk.finish_reason,
                            }],
                        }
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logger.error(f"中转站流式调用失败: {e}")
                    error_data = {"error": {"message": str(e), "type": "relay_error"}}
                    yield f"data: {json.dumps(error_data)}\n\n"

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # 非流式模式
            response = await relay_service.chat_completions(
                db=db,
                model_id=data.model,
                messages=messages,
                stream=False,
                temperature=data.temperature,
                max_tokens=data.max_tokens,
                top_p=data.top_p,
            )

            return {
                "id": "chatcmpl-relay",
                "object": "chat.completion",
                "created": 0,
                "model": response.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response.content,
                    },
                    "finish_reason": response.finish_reason,
                }],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"中转站调用失败: {e}")
        raise HTTPException(status_code=500, detail=f"调用失败: {str(e)}")
