"""Chat room management routes."""
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services import data_store, chat_manager

router = APIRouter(prefix="/api/chatroom", tags=["chatroom"])


class BotConfig(BaseModel):
    model: str
    nick: str = ""
    persona: str = ""
    color: str = ""
    system_prompt: str = ""


class CreateRoomRequest(BaseModel):
    system: str = ""
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 2048
    thinking_mode: Optional[str] = None  # None=auto, "on", "off"
    bots: list[BotConfig] = []


class SendMessageRequest(BaseModel):
    room_id: str
    message: str


@router.post("/create")
async def create_chatroom(req: CreateRoomRequest):
    """Create and start a new chat room with custom bot configs."""
    configs = await data_store.read_json("api_configs.json")
    if not isinstance(configs, list):
        configs = []

    config_map = {c["id"]: c for c in configs}
    bot_configs = []
    for bot in req.bots:
        # Find config that has this model
        matched_cfg = None
        for cfg in configs:
            models = cfg.get("models", [])
            model_strs = [m if isinstance(m, str) else m.get("name", "") for m in models]
            if bot.model in model_strs:
                matched_cfg = cfg
                break
        if not matched_cfg:
            # Try matching by config_id:model format
            parts = bot.model.split(":", 1)
            if len(parts) == 2:
                matched_cfg = config_map.get(parts[0])
        if matched_cfg:
            bot_configs.append({
                "config_id": matched_cfg["id"],
                "model": bot.model.split(":", 1)[-1] if ":" in bot.model else bot.model,
                "nick": bot.nick,
                "persona": bot.persona,
                "color": bot.color,
                "system_prompt": bot.system_prompt,
            })

    if not bot_configs:
        raise HTTPException(status_code=400, detail="没有匹配到有效的模型配置")

    room = await chat_manager.create_room_with_bots(
        bot_configs=bot_configs,
        configs_data=configs,
        system_prompt=req.system,
        temperature=req.temperature,
        top_p=req.top_p,
        max_tokens=req.max_tokens,
        thinking_mode=req.thinking_mode,
    )
    return {
        "room_id": room["room_id"],
        "bots": room["bots"],
        "created_at": room["created_at"],
    }


@router.post("/message")
async def send_message(req: SendMessageRequest):
    """Send a message to a chat room and stream responses."""
    configs = await data_store.read_json("api_configs.json")
    if not isinstance(configs, list):
        configs = []

    async def event_stream():
        async for event in chat_manager.send_message(req.room_id, req.message, configs):
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/{room_id}/stop")
async def stop_chatroom(room_id: str):
    """Stop a chat room and persist history."""
    success = await chat_manager.stop_room(room_id)
    if not success:
        raise HTTPException(status_code=404, detail="聊天室不存在")
    return {"success": True}


@router.post("/{room_id}/clear")
async def clear_chatroom(room_id: str):
    """Clear messages in a chat room."""
    success = await chat_manager.clear_room_history(room_id)
    if not success:
        raise HTTPException(status_code=404, detail="聊天室不存在")
    return {"success": True}


@router.get("/{room_id}/history")
async def get_room_history(room_id: str):
    """Get message history for a chat room."""
    room = await chat_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="聊天室不存在")
    return {
        "room_id": room["room_id"],
        "messages": room["messages"],
        "bots": room["bots"],
    }
