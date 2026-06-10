"""Chat room manager with multi-model support and context management."""
import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator

from . import llm_client
from . import data_store

# 50 preset nicknames
NICKNAMES = [
    "星辰", "月影", "风铃", "云鹤", "雪松",
    "竹韵", "梅香", "兰亭", "菊隐", "松涛",
    "剑客", "琴心", "棋圣", "书痴", "画仙",
    "青龙", "白虎", "朱雀", "玄武", "麒麟",
    "流光", "飞羽", "落霞", "孤烟", "长风",
    "明月", "清泉", "碧海", "蓝天", "紫霞",
    "飞鸿", "游龙", "卧虎", "藏鹰", "隐凤",
    "听雨", "望月", "踏雪", "摘星", "揽月",
    "浮云", "流水", "行风", "追光", "逐影",
    "墨竹", "幽兰", "寒梅", "傲菊", "苍松",
]

PERSONAS = [
    "逻辑严谨的学者", "风趣幽默的段子手", "文艺浪漫的诗人",
    "理性冷静的分析师", "热情洋溢的演说家", "深沉内敛的哲人",
    "机智敏捷的辩论家", "温和耐心的导师", "犀利尖锐的评论家",
    "天马行空的创意者", "实事求是的工程师", "博学多闻的百科全书",
]

AVATAR_COLORS = [
    "#6c5ce7", "#00b894", "#e17055", "#0984e3", "#d63031",
    "#fdcb6e", "#e84393", "#00cec9", "#a29bfe", "#fab1a0",
]

# In-memory room storage
_active_rooms: Dict[str, Dict[str, Any]] = {}


def _assign_nickname(used: set) -> str:
    """Assign a random nickname not already used."""
    import random
    available = [n for n in NICKNAMES if n not in used]
    if not available:
        available = NICKNAMES
    return random.choice(available)


def _assign_persona() -> str:
    """Assign a random persona."""
    import random
    return random.choice(PERSONAS)


async def create_room(
    config_ids: list[str],
    configs_data: list[Dict[str, Any]],
    system_prompt: str = "",
    temperature: float = 0.7,
    top_p: float = 1.0,
    max_tokens: int = 2048,
    thinking_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new chat room with selected models."""
    room_id = str(uuid.uuid4())[:8]
    used_nicknames = set()
    bots = []

    config_map = {c["id"]: c for c in configs_data}
    for idx, cid in enumerate(config_ids):
        cfg = config_map.get(cid)
        if not cfg:
            continue
        model = cfg.get("models", [None])[0] if cfg.get("models") else None
        if not model:
            continue
        nickname = _assign_nickname(used_nicknames)
        used_nicknames.add(nickname)
        persona = _assign_persona()
        bots.append({
            "bot_id": str(uuid.uuid4())[:8],
            "config_id": cid,
            "config_name": cfg.get("name", ""),
            "model": model,
            "nickname": nickname,
            "persona": persona,
            "color": AVATAR_COLORS[idx % len(AVATAR_COLORS)],
        })

    room = {
        "room_id": room_id,
        "created_at": datetime.now().isoformat(),
        "system_prompt": system_prompt,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "thinking_mode": thinking_mode,
        "bots": bots,
        "messages": [],
        "context_rounds": 6,
    }
    _active_rooms[room_id] = room
    return room


async def create_room_with_bots(
    bot_configs: list[Dict[str, Any]],
    configs_data: list[Dict[str, Any]],
    system_prompt: str = "",
    temperature: float = 0.7,
    top_p: float = 1.0,
    max_tokens: int = 2048,
    thinking_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new chat room with explicit bot configurations."""
    room_id = str(uuid.uuid4())[:8]
    config_map = {c["id"]: c for c in configs_data}
    bots = []
    used_nicknames = set()

    for idx, bc in enumerate(bot_configs):
        cfg = config_map.get(bc["config_id"])
        if not cfg:
            continue
        nickname = bc.get("nick") or _assign_nickname(used_nicknames)
        used_nicknames.add(nickname)
        persona = bc.get("persona") or _assign_persona()
        color = bc.get("color") or AVATAR_COLORS[idx % len(AVATAR_COLORS)]
        bots.append({
            "bot_id": str(uuid.uuid4())[:8],
            "config_id": bc["config_id"],
            "config_name": cfg.get("name", ""),
            "model": bc["model"],
            "nickname": nickname,
            "persona": persona,
            "color": color,
            "system_prompt": bc.get("system_prompt", ""),
        })

    room = {
        "room_id": room_id,
        "created_at": datetime.now().isoformat(),
        "system_prompt": system_prompt,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "thinking_mode": thinking_mode,
        "bots": bots,
        "messages": [],
        "context_rounds": 6,
    }
    _active_rooms[room_id] = room
    return room


async def get_room(room_id: str) -> Optional[Dict[str, Any]]:
    """Get an active room by ID."""
    return _active_rooms.get(room_id)


async def stop_room(room_id: str) -> bool:
    """Stop a room and persist its history."""
    room = _active_rooms.pop(room_id, None)
    if not room:
        return False
    history = await data_store.read_json("chat_history.json")
    if not isinstance(history, list):
        history = []
    history.append({
        "room_id": room["room_id"],
        "created_at": room["created_at"],
        "system_prompt": room["system_prompt"],
        "bots": room["bots"],
        "messages": room["messages"],
    })
    await data_store.write_json("chat_history.json", history)
    return True


async def send_message(
    room_id: str,
    user_message: str,
    configs_data: list[Dict[str, Any]],
) -> AsyncGenerator[str, None]:
    """Send a message to the room and stream all bot responses."""
    room = _active_rooms.get(room_id)
    if not room:
        yield f"data: {json.dumps({'type': 'error', 'message': '聊天室不存在'})}\n\n"
        return

    # Add user message to history
    room["messages"].append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat(),
    })

    # Build context: system prompt + recent messages
    config_map = {c["id"]: c for c in configs_data}
    context_rounds = room.get("context_rounds", 6)
    recent = room["messages"][-(context_rounds * 2 + 1):]

    # Process each bot
    async def process_bot(bot: Dict[str, Any]):
        cfg = config_map.get(bot["config_id"])
        if not cfg:
            return
        messages = []
        # Per-bot system prompt takes priority over room system prompt
        bot_sys = bot.get("system_prompt", "")
        sys_prompt = bot_sys if bot_sys else room.get("system_prompt", "")
        if sys_prompt:
            messages.append({"role": "system", "content": sys_prompt})

        for msg in recent:
            if msg["role"] == "user":
                messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "bot":
                # Format other bot messages as user context
                bn = msg.get("nickname", "Bot")
                messages.append({"role": "user", "content": f"【{bn}】说：{msg['content']}"})

        bot_id = bot["bot_id"]
        # Notify bot start
        start_event = {
            "type": "bot_start",
            "bot_id": bot_id,
            "nickname": bot["nickname"],
            "persona": bot["persona"],
            "color": bot["color"],
            "model": bot["model"],
        }
        yield_start = json.dumps(start_event)

        try:
            start_time = time.perf_counter()
            result = await llm_client.send_chat(
                base_url=cfg["base_url"],
                api_key=cfg["api_key"],
                model=bot["model"],
                messages=messages,
                temperature=room["temperature"],
                max_tokens=room["max_tokens"],
                top_p=room["top_p"],
                timeout=cfg.get("timeout", 120),
                proxy=cfg.get("proxy"),
                thinking_mode=room.get("thinking_mode"),
            )
            total_time = time.perf_counter() - start_time

            if result.get("success"):
                content = result["content"]
                reasoning = result.get("reasoning", "")
                room["messages"].append({
                    "role": "bot",
                    "bot_id": bot_id,
                    "nickname": bot["nickname"],
                    "content": content,
                    "reasoning": reasoning,
                    "ttfb": result.get("ttfb", 0),
                    "speed": result.get("tokens_per_sec", 0),
                    "completion_tokens": result.get("completion_tokens", 0),
                    "thinking_time": result.get("thinking_time", 0),
                    "time": round(total_time, 3),
                    "timestamp": datetime.now().isoformat(),
                })
                return json.dumps({
                    "type": "bot_done",
                    "bot_id": bot_id,
                    "nickname": bot["nickname"],
                    "content": content,
                    "reasoning": reasoning,
                    "ttfb": result.get("ttfb", 0),
                    "speed": result.get("tokens_per_sec", 0),
                    "completion_tokens": result.get("completion_tokens", 0),
                    "thinking_time": result.get("thinking_time", 0),
                    "time": round(total_time, 3),
                    "color": bot["color"],
                    "persona": bot["persona"],
                })
            else:
                return json.dumps({
                    "type": "bot_error",
                    "bot_id": bot_id,
                    "nickname": bot["nickname"],
                    "message": result.get("message", "请求失败"),
                    "color": bot["color"],
                })
        except Exception as e:
            return json.dumps({
                "type": "bot_error",
                "bot_id": bot_id,
                "nickname": bot["nickname"],
                "message": str(e)[:200],
                "color": bot["color"],
            })

    # Yield all bot start events
    for bot in room["bots"]:
        start_event = {
            "type": "bot_start",
            "bot_id": bot["bot_id"],
            "nickname": bot["nickname"],
            "persona": bot["persona"],
            "color": bot["color"],
            "model": bot["model"],
        }
        yield f"data: {json.dumps(start_event)}\n\n"

    # Run all bots concurrently
    coros = [process_bot(bot) for bot in room["bots"]]
    results = await asyncio.gather(*coros, return_exceptions=True)
    for r in results:
        if isinstance(r, str):
            yield f"data: {r}\n\n"
        elif isinstance(r, Exception):
            yield f"data: {json.dumps({'type': 'bot_error', 'message': str(r)[:200]})}\n\n"

    yield f"data: {json.dumps({'type': 'all_done'})}\n\n"


async def clear_room_history(room_id: str) -> bool:
    """Clear messages in a room."""
    room = _active_rooms.get(room_id)
    if not room:
        return False
    room["messages"] = []
    return True


def get_all_rooms() -> list[Dict[str, Any]]:
    """Get all active rooms."""
    return [
        {"room_id": r["room_id"], "created_at": r["created_at"],
         "bots": [{"nickname": b["nickname"], "model": b["model"]} for b in r["bots"]],
         "message_count": len(r["messages"])}
        for r in _active_rooms.values()
    ]
