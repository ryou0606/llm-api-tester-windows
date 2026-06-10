"""History record routes."""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ..services import data_store

router = APIRouter(prefix="/api/history", tags=["history"])

HISTORY_FILES = {
    "speed": "speed_history.json",
    "duel": "duel_history.json",
    "debate": "debate_history.json",
    "roundtable": "roundtable_history.json",
}


@router.get("")
async def get_history(type: str = Query("speed")):
    """Get history records by type."""
    filename = HISTORY_FILES.get(type)
    if not filename:
        raise HTTPException(status_code=400, detail=f"Unknown type: {type}")
    history = await data_store.read_json(filename)
    return history if isinstance(history, list) else []


@router.delete("")
async def clear_history(type: str = Query("speed")):
    """Clear all history records of a type."""
    filename = HISTORY_FILES.get(type)
    if not filename:
        raise HTTPException(status_code=400, detail=f"Unknown type: {type}")
    await data_store.write_json(filename, [])
    return {"success": True}


@router.delete("/{item_id}")
async def delete_history_item(item_id: str, type: str = Query("speed")):
    """Delete a single history record."""
    filename = HISTORY_FILES.get(type)
    if not filename:
        raise HTTPException(status_code=400, detail=f"Unknown type: {type}")
    history = await data_store.read_json(filename)
    if not isinstance(history, list):
        history = []
    new_history = [h for h in history if h.get("id") != item_id]
    if len(new_history) == len(history):
        raise HTTPException(status_code=404, detail="记录不存在")
    await data_store.write_json(filename, new_history)
    return {"success": True}


# Keep specific routes for backward compatibility
@router.get("/speed")
async def get_speed_history():
    history = await data_store.read_json("speed_history.json")
    return history if isinstance(history, list) else []


@router.delete("/speed")
async def clear_speed_history():
    await data_store.write_json("speed_history.json", [])
    return {"success": True}


@router.delete("/speed/{item_id}")
async def delete_speed_item(item_id: str):
    history = await data_store.read_json("speed_history.json")
    if not isinstance(history, list):
        history = []
    new_history = [h for h in history if h.get("id") != item_id]
    if len(new_history) == len(history):
        raise HTTPException(status_code=404, detail="记录不存在")
    await data_store.write_json("speed_history.json", new_history)
    return {"success": True}


@router.get("/duel")
async def get_duel_history():
    history = await data_store.read_json("duel_history.json")
    return history if isinstance(history, list) else []


@router.delete("/duel")
async def clear_duel_history():
    await data_store.write_json("duel_history.json", [])
    return {"success": True}


@router.delete("/duel/{item_id}")
async def delete_duel_item(item_id: str):
    history = await data_store.read_json("duel_history.json")
    if not isinstance(history, list):
        history = []
    new_history = [h for h in history if h.get("id") != item_id]
    if len(new_history) == len(history):
        raise HTTPException(status_code=404, detail="记录不存在")
    await data_store.write_json("duel_history.json", new_history)
    return {"success": True}


@router.get("/debate")
async def get_debate_history():
    history = await data_store.read_json("debate_history.json")
    return history if isinstance(history, list) else []


@router.delete("/debate")
async def clear_debate_history():
    await data_store.write_json("debate_history.json", [])
    return {"success": True}


@router.delete("/debate/{item_id}")
async def delete_debate_item(item_id: str):
    history = await data_store.read_json("debate_history.json")
    if not isinstance(history, list):
        history = []
    new_history = [h for h in history if h.get("id") != item_id]
    if len(new_history) == len(history):
        raise HTTPException(status_code=404, detail="记录不存在")
    await data_store.write_json("debate_history.json", new_history)
    return {"success": True}


@router.get("/roundtable")
async def get_roundtable_history():
    history = await data_store.read_json("roundtable_history.json")
    return history if isinstance(history, list) else []


@router.delete("/roundtable")
async def clear_roundtable_history():
    await data_store.write_json("roundtable_history.json", [])
    return {"success": True}


@router.delete("/roundtable/{item_id}")
async def delete_roundtable_item(item_id: str):
    history = await data_store.read_json("roundtable_history.json")
    if not isinstance(history, list):
        history = []
    new_history = [h for h in history if h.get("id") != item_id]
    if len(new_history) == len(history):
        raise HTTPException(status_code=404, detail="记录不存在")
    await data_store.write_json("roundtable_history.json", new_history)
    return {"success": True}


@router.get("/all")
async def get_all_history():
    speed = await data_store.read_json("speed_history.json")
    duel = await data_store.read_json("duel_history.json")
    debate = await data_store.read_json("debate_history.json")
    roundtable = await data_store.read_json("roundtable_history.json")
    return {
        "speed": speed if isinstance(speed, list) else [],
        "duel": duel if isinstance(duel, list) else [],
        "debate": debate if isinstance(debate, list) else [],
        "roundtable": roundtable if isinstance(roundtable, list) else [],
    }


@router.delete("/all")
async def clear_all_history():
    await data_store.write_json("speed_history.json", [])
    await data_store.write_json("duel_history.json", [])
    await data_store.write_json("debate_history.json", [])
    await data_store.write_json("roundtable_history.json", [])
    return {"success": True}


@router.get("/all/export")
async def export_all_history():
    speed = await data_store.read_json("speed_history.json")
    duel = await data_store.read_json("duel_history.json")
    debate = await data_store.read_json("debate_history.json")
    roundtable = await data_store.read_json("roundtable_history.json")
    return {
        "speed": speed if isinstance(speed, list) else [],
        "duel": duel if isinstance(duel, list) else [],
        "debate": debate if isinstance(debate, list) else [],
        "roundtable": roundtable if isinstance(roundtable, list) else [],
    }
