"""Roundtable (multi-model discussion) routes."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..models import RoundtableCreateRequest, RoundtableMessageRequest
from ..services import data_store, roundtable_manager

router = APIRouter(prefix="/api/roundtable", tags=["roundtable"])


@router.post("/create")
async def create_roundtable(req: RoundtableCreateRequest):
    """Create a new roundtable room."""
    configs = await data_store.read_json("api_configs.json")
    if not isinstance(configs, list):
        configs = []

    try:
        room = await roundtable_manager.create_room(
            topic=req.topic,
            participants_config=[p.model_dump() for p in req.participants],
            configs_data=configs,
            context_rounds=req.context_rounds,
            temperature=req.temperature,
            top_p=req.top_p,
            max_tokens=req.max_tokens,
            thinking_mode=req.thinking_mode,
            hide_user_identity=req.hide_user_identity,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Add topic as first user message
    room["messages"].append({
        "role": "user",
        "content": req.topic,
        "round": 0,
        "timestamp": room["created_at"],
    })

    return {
        "room_id": room["room_id"],
        "participants": room["participants"],
        "topic": room["topic"],
        "created_at": room["created_at"],
        "hide_user_identity": room.get("hide_user_identity", False),
        "user_nick": room.get("user_nick", ""),
    }


@router.post("/{room_id}/next-round")
async def next_round(room_id: str):
    """Start the next round: all participants speak in parallel."""
    configs = await data_store.read_json("api_configs.json")
    if not isinstance(configs, list):
        configs = []

    room = await roundtable_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="圆桌不存在")
    if room.get("round_active"):
        raise HTTPException(status_code=400, detail="当前轮次尚未结束")

    async def event_stream():
        async for event in roundtable_manager.start_round(room_id, configs):
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/{room_id}/end-round")
async def end_round(room_id: str):
    """Mark the current round as ended (user confirms they've read all messages)."""
    room = await roundtable_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="圆桌不存在")
    room["round_active"] = False
    return {"success": True, "round": room["current_round"]}


@router.post("/{room_id}/message")
async def send_message(room_id: str, req: RoundtableMessageRequest):
    """Add a user message between rounds."""
    success = await roundtable_manager.add_user_message(room_id, req.message)
    if not success:
        raise HTTPException(status_code=404, detail="圆桌不存在")
    return {"success": True}


@router.post("/{room_id}/stop")
async def stop_roundtable(room_id: str):
    """Stop the roundtable and save history."""
    success = await roundtable_manager.stop_room(room_id)
    if not success:
        raise HTTPException(status_code=404, detail="圆桌不存在")
    return {"success": True}


@router.post("/{room_id}/clear")
async def clear_roundtable(room_id: str):
    """Clear messages in a roundtable room."""
    success = await roundtable_manager.clear_room_history(room_id)
    if not success:
        raise HTTPException(status_code=404, detail="圆桌不存在")
    return {"success": True}


@router.get("/{room_id}/history")
async def get_room_history(room_id: str):
    """Get message history for a roundtable room."""
    room = await roundtable_manager.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="圆桌不存在")
    return {
        "room_id": room["room_id"],
        "messages": room["messages"],
        "participants": room["participants"],
        "current_round": room["current_round"],
        "round_active": room["round_active"],
    }
