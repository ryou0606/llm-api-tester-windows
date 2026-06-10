"""Roundtable manager: multi-model free discussion with cross-visibility."""
import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator

from . import llm_client
from . import data_store

# Reuse nickname/color pools from chat_manager
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
    import random
    available = [n for n in NICKNAMES if n not in used]
    if not available:
        available = NICKNAMES
    return random.choice(available)


def _assign_persona() -> str:
    import random
    return random.choice(PERSONAS)


async def create_room(
    topic: str,
    participants_config: list[Dict[str, Any]],
    configs_data: list[Dict[str, Any]],
    context_rounds: int = 6,
    temperature: float = 0.7,
    top_p: float = 1.0,
    max_tokens: Optional[int] = None,
    thinking_mode: Optional[str] = None,
    hide_user_identity: bool = False,
) -> Dict[str, Any]:
    """Create a new roundtable room."""
    room_id = str(uuid.uuid4())[:8]
    config_map = {c["id"]: c for c in configs_data}
    participants = []
    used_nicks = set()

    for idx, pc in enumerate(participants_config):
        # Match config
        matched_cfg = None
        model_name = pc.get("model", "")
        for cfg in configs_data:
            models = cfg.get("models", [])
            model_strs = [m if isinstance(m, str) else m.get("name", "") for m in models]
            if model_name in model_strs:
                matched_cfg = cfg
                break
        if not matched_cfg:
            parts = model_name.split(":", 1)
            if len(parts) == 2:
                matched_cfg = config_map.get(parts[0])
        if not matched_cfg:
            continue

        nick = pc.get("nick") or _assign_nickname(used_nicks)
        used_nicks.add(nick)
        persona = pc.get("persona") or _assign_persona()
        color = pc.get("color") or AVATAR_COLORS[idx % len(AVATAR_COLORS)]

        participants.append({
            "participant_id": str(uuid.uuid4())[:8],
            "config_id": matched_cfg["id"],
            "config_name": matched_cfg.get("name", ""),
            "model": model_name.split(":", 1)[-1] if ":" in model_name else model_name,
            "nick": nick,
            "persona": persona,
            "color": color,
            "system_prompt": pc.get("system_prompt", ""),
        })

    if not participants:
        raise ValueError("没有匹配到有效的模型配置")

    # Assign user a random nick if hiding identity
    user_nick = ""
    if hide_user_identity:
        user_nick = _assign_nickname(used_nicks)

    room = {
        "room_id": room_id,
        "created_at": datetime.now().isoformat(),
        "topic": topic,
        "context_rounds": context_rounds,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "thinking_mode": thinking_mode,
        "hide_user_identity": hide_user_identity,
        "user_nick": user_nick,
        "participants": participants,
        "messages": [],
        "current_round": 0,
        "round_active": False,
    }
    _active_rooms[room_id] = room
    return room


async def get_room(room_id: str) -> Optional[Dict[str, Any]]:
    return _active_rooms.get(room_id)


async def start_round(
    room_id: str,
    configs_data: list[Dict[str, Any]],
) -> AsyncGenerator[str, None]:
    """Start a new round: all participants speak in parallel, first-done-first-shown."""
    room = _active_rooms.get(room_id)
    if not room:
        yield f"data: {json.dumps({'type': 'error', 'message': '圆桌不存在'})}\n\n"
        return

    room["current_round"] += 1
    room["round_active"] = True
    current_round = room["current_round"]

    # Emit round_start
    yield f"data: {json.dumps({'type': 'round_start', 'round': current_round})}\n\n"

    config_map = {c["id"]: c for c in configs_data}
    context_rounds = room.get("context_rounds", 6)

    # Build shared context from recent messages
    context_messages = _build_context(room["messages"], context_rounds)

    async def speak(participant: Dict[str, Any]) -> str:
        cfg = config_map.get(participant["config_id"])
        if not cfg:
            return json.dumps({
                "type": "participant_error",
                "participant_id": participant["participant_id"],
                "nick": participant["nick"],
                "message": "配置未找到",
                "color": participant["color"],
            })

        messages = []
        # System prompt: auto-inject identity, then append user's custom prompt
        identity_line = f"你是【{participant['nick']}】，正在参与一场多人圆桌讨论。其他参与者的发言会以【昵称】说：的格式呈现。当提到你的昵称时，就是在引用你的观点。"
        user_sys = participant.get("system_prompt", "")
        if user_sys:
            full_sys = identity_line + "\n\n" + user_sys
        else:
            full_sys = identity_line
        messages.append({"role": "system", "content": full_sys})

        # Add context: user messages + other participants' messages (skip own)
        pid = participant["participant_id"]
        hide_identity = room.get("hide_user_identity", False)
        user_nick = room.get("user_nick", "用户")
        for msg in context_messages:
            if msg["role"] == "user":
                if hide_identity:
                    # Format user message same as participant
                    messages.append({"role": "user", "content": f"【{user_nick}】说：{msg['content']}"})
                else:
                    messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "participant":
                if msg.get("participant_id") == pid:
                    # Skip own previous messages
                    continue
                nick = msg.get("nick", "参与者")
                messages.append({"role": "user", "content": f"【{nick}】说：{msg['content']}"})

        pid = participant["participant_id"]
        try:
            start_time = time.perf_counter()
            result = await llm_client.send_chat(
                base_url=cfg["base_url"],
                api_key=cfg["api_key"],
                model=participant["model"],
                messages=messages,
                temperature=room["temperature"],
                max_tokens=room["max_tokens"] or 128000,
                top_p=room["top_p"],
                timeout=cfg.get("timeout", 120),
                proxy=cfg.get("proxy"),
                thinking_mode=room.get("thinking_mode"),
            )
            total_time = time.perf_counter() - start_time

            if result.get("success"):
                content = result["content"]
                reasoning = result.get("reasoning", "")
                # Save to room messages
                room["messages"].append({
                    "role": "participant",
                    "participant_id": pid,
                    "nick": participant["nick"],
                    "content": content,
                    "reasoning": reasoning,
                    "round": current_round,
                    "ttfb": result.get("ttfb", 0),
                    "speed": result.get("tokens_per_sec", 0),
                    "completion_tokens": result.get("completion_tokens", 0),
                    "thinking_time": result.get("thinking_time", 0),
                    "time": round(total_time, 3),
                    "timestamp": datetime.now().isoformat(),
                })
                return json.dumps({
                    "type": "participant_done",
                    "participant_id": pid,
                    "nick": participant["nick"],
                    "content": content,
                    "reasoning": reasoning,
                    "ttfb": result.get("ttfb", 0),
                    "speed": result.get("tokens_per_sec", 0),
                    "completion_tokens": result.get("completion_tokens", 0),
                    "thinking_time": result.get("thinking_time", 0),
                    "time": round(total_time, 3),
                    "color": participant["color"],
                    "persona": participant["persona"],
                    "round": current_round,
                })
            else:
                return json.dumps({
                    "type": "participant_error",
                    "participant_id": pid,
                    "nick": participant["nick"],
                    "message": result.get("message", "请求失败"),
                    "color": participant["color"],
                })
        except Exception as e:
            return json.dumps({
                "type": "participant_error",
                "participant_id": pid,
                "nick": participant["nick"],
                "message": str(e)[:200],
                "color": participant["color"],
            })

    # Emit participant_start for all
    for p in room["participants"]:
        yield f"data: {json.dumps({'type': 'participant_start', 'participant_id': p['participant_id'], 'nick': p['nick'], 'color': p['color'], 'model': p['model']})}\n\n"

    # Run all concurrently, yield results as they complete
    tasks = {asyncio.create_task(speak(p)): p for p in room["participants"]}
    done_count = 0
    for coro in asyncio.as_completed(tasks.keys()):
        result = await coro
        yield f"data: {result}\n\n"
        done_count += 1

    room["round_active"] = False
    yield f"data: {json.dumps({'type': 'round_done', 'round': current_round})}\n\n"


async def add_user_message(room_id: str, message: str) -> bool:
    """Add a user message (between rounds)."""
    room = _active_rooms.get(room_id)
    if not room:
        return False
    room["messages"].append({
        "role": "user",
        "content": message,
        "round": room["current_round"],
        "timestamp": datetime.now().isoformat(),
    })
    return True


async def stop_room(room_id: str) -> bool:
    """Stop a roundtable and persist history."""
    room = _active_rooms.pop(room_id, None)
    if not room:
        return False
    history = await data_store.read_json("roundtable_history.json")
    if not isinstance(history, list):
        history = []
    history.insert(0, {
        "id": str(uuid.uuid4())[:8],
        "topic": room["topic"],
        "created_at": room["created_at"],
        "participants": [
            {"nick": p["nick"], "model": p["model"], "persona": p["persona"], "color": p["color"]}
            for p in room["participants"]
        ],
        "params": {
            "context_rounds": room["context_rounds"],
            "temperature": room["temperature"],
            "top_p": room["top_p"],
            "max_tokens": room["max_tokens"],
            "hide_user_identity": room.get("hide_user_identity", False),
            "user_nick": room.get("user_nick", ""),
        },
        "messages": room["messages"],
        "total_rounds": room["current_round"],
    })
    # Keep last 100 records
    history = history[:100]
    await data_store.write_json("roundtable_history.json", history)
    return True


async def clear_room_history(room_id: str) -> bool:
    """Clear messages in a roundtable room."""
    room = _active_rooms.get(room_id)
    if not room:
        return False
    room["messages"] = []
    room["current_round"] = 0
    room["round_active"] = False
    return True


def _build_context(messages: list, context_rounds: int) -> list:
    """
    Build context: take all messages from the last `context_rounds` rounds.
    A "round" is delimited by round_start markers or user messages.
    """
    if not messages:
        return []

    # Find round boundaries (indices where round number changes)
    round_starts = []
    for i, msg in enumerate(messages):
        if msg.get("role") == "round_start" or (msg.get("role") == "participant" and msg.get("round")):
            r = msg.get("round", 0)
            if not round_starts or round_starts[-1][0] != r:
                round_starts.append((r, i))

    if not round_starts:
        return messages

    # Get the starting index for the context window
    # We want the last `context_rounds` rounds
    if len(round_starts) <= context_rounds:
        start_idx = 0
    else:
        start_idx = round_starts[-(context_rounds)][1]

    return messages[start_idx:]
