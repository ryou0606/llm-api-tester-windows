"""Speed testing service with concurrency control and overload protection."""
import asyncio
import json
import math
import time
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional

import psutil

from . import llm_client


def _get_effective_concurrency(requested: int) -> int:
    """Reduce concurrency if CPU or memory usage is too high."""
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory().percent
    if cpu > 90 or mem > 90:
        return min(requested, 2)
    if cpu > 75 or mem > 75:
        return min(requested, 5)
    return requested


def _stddev(values: list[float]) -> float:
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


async def run_speed_test(
    configs: list[Dict[str, Any]],
    prompt: str,
    system_prompt: str,
    rounds: int,
    concurrency: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
) -> AsyncGenerator[str, None]:
    """
    Run speed tests across multiple API configs/models.
    Yields SSE-formatted events.
    """
    test_id = str(uuid.uuid4())[:8]
    total_tasks = len(configs) * rounds
    completed = 0
    results: Dict[str, Dict[str, Any]] = {}

    # Initialize result accumulators for each config
    for cfg in configs:
        key = f"{cfg['id']}_{cfg.get('model', '')}"
        results[key] = {
            "config_id": cfg["id"],
            "config_name": cfg.get("name", ""),
            "model": cfg.get("model", ""),
            "ttfbs": [],
            "speeds": [],
            "times": [],
            "success": 0,
            "fail": 0,
            "errors": [],
        }

    yield f"data: {json.dumps({'type': 'start', 'test_id': test_id, 'total': total_tasks})}\n\n"

    semaphore_value = _get_effective_concurrency(concurrency)
    semaphore = asyncio.Semaphore(semaphore_value)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    async def run_single(cfg: Dict, round_num: int):
        nonlocal completed
        key = f"{cfg['id']}_{cfg.get('model', '')}"
        r = results[key]
        effective_conc = _get_effective_concurrency(concurrency)
        if effective_conc != semaphore._value:
            # Adjust semaphore if needed (best effort)
            pass

        async with semaphore:
            try:
                result = await llm_client.send_chat(
                    base_url=cfg["base_url"],
                    api_key=cfg["api_key"],
                    model=cfg.get("model", ""),
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    timeout=cfg.get("timeout", 120),
                    proxy=cfg.get("proxy"),
                )
                if result.get("success"):
                    r["ttfbs"].append(result["ttfb"])
                    r["speeds"].append(result["tokens_per_sec"])
                    r["times"].append(result["total_time"])
                    r["success"] += 1
                    status = "success"
                else:
                    r["fail"] += 1
                    r["errors"].append(result.get("message", "未知错误"))
                    status = "fail"
            except Exception as e:
                r["fail"] += 1
                r["errors"].append(str(e)[:200])
                status = "fail"
                result = {"ttfb": 0, "total_time": 0, "tokens_per_sec": 0}

            completed += 1
            yield_data = {
                "type": "progress",
                "completed": completed,
                "total": total_tasks,
                "config_id": cfg["id"],
                "config_name": cfg.get("name", ""),
                "model": cfg.get("model", ""),
                "round": round_num,
                "status": status,
                "ttfb": result.get("ttfb", 0),
                "speed": result.get("tokens_per_sec", 0),
                "time": result.get("total_time", 0),
            }
            return json.dumps(yield_data)

    # Run all tasks
    tasks_coros = []
    for cfg in configs:
        for r_num in range(1, rounds + 1):
            tasks_coros.append(run_single(cfg, r_num))

    # Process in batches to yield progress
    batch_size = max(1, semaphore_value)
    for i in range(0, len(tasks_coros), batch_size):
        batch = tasks_coros[i:i + batch_size]
        done_results = await asyncio.gather(*batch, return_exceptions=True)
        for dr in done_results:
            if isinstance(dr, str):
                yield f"data: {dr}\n\n"
            elif isinstance(dr, Exception):
                yield f"data: {json.dumps({'type': 'progress', 'status': 'fail', 'error': str(dr)[:200]})}\n\n"

    # Build final summary
    summary = []
    for key, r in results.items():
        total = r["success"] + r["fail"]
        summary.append({
            "config_id": r["config_id"],
            "config_name": r["config_name"],
            "model": r["model"],
            "total_rounds": total,
            "success": r["success"],
            "fail": r["fail"],
            "success_rate": round(r["success"] / total * 100, 1) if total else 0,
            "avg_ttfb": round(sum(r["ttfbs"]) / len(r["ttfbs"]), 3) if r["ttfbs"] else 0,
            "ttfb_stddev": round(_stddev(r["ttfbs"]), 3) if r["ttfbs"] else 0,
            "avg_speed": round(sum(r["speeds"]) / len(r["speeds"]), 2) if r["speeds"] else 0,
            "speed_stddev": round(_stddev(r["speeds"]), 2) if r["speeds"] else 0,
            "fastest": round(min(r["times"]), 3) if r["times"] else 0,
            "slowest": round(max(r["times"]), 3) if r["times"] else 0,
            "errors": list(set(r["errors"]))[:5],
        })

    history_entry = {
        "id": test_id,
        "timestamp": datetime.now().isoformat(),
        "params": {
            "prompt": prompt,
            "system_prompt": system_prompt,
            "rounds": rounds,
            "concurrency": concurrency,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        },
        "results": summary,
    }

    yield f"data: {json.dumps({'type': 'complete', 'results': summary, 'history': history_entry})}\n\n"
