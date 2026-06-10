"""Async LLM client using httpx for OpenAI-compatible APIs."""
import asyncio
import time
import json
from typing import Optional, AsyncGenerator, Dict, Any

import httpx


async def fetch_models(base_url: str, api_key: str, timeout: int = 30,
                       proxy: Optional[str] = None) -> list[str]:
    """Fetch available models from the API endpoint.
    Tries multiple URL patterns and response formats for compatibility."""
    headers = {"Authorization": f"Bearer {api_key}"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    base = base_url.rstrip("/")

    # Build candidate URLs to try
    urls_to_try = []
    if base.endswith("/v1"):
        urls_to_try.append(base + "/models")
    elif base.endswith("/v1/"):
        urls_to_try.append(base + "models")
    else:
        urls_to_try.append(base + "/v1/models")
        urls_to_try.append(base + "/models")

    last_error = None
    async with httpx.AsyncClient(timeout=timeout, proxy=proxy) as client:
        for url in urls_to_try:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                data = resp.json()
                return _parse_model_list(data)
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                continue
            except httpx.ConnectError as e:
                last_error = f"Connection failed: {e}"
                continue
            except httpx.TimeoutException:
                last_error = "Request timeout"
                continue
            except Exception as e:
                last_error = str(e)[:200]
                continue

    raise RuntimeError(last_error or "Failed to fetch models from all endpoints")


def _parse_model_list(data: Any) -> list[str]:
    """Parse model list from various API response formats."""
    models = []

    # Format 1: OpenAI style { "data": [ { "id": "model-name" } ] }
    if isinstance(data, dict) and "data" in data:
        items = data["data"]
        if isinstance(items, list):
            for m in items:
                if isinstance(m, str):
                    models.append(m)
                elif isinstance(m, dict):
                    mid = m.get("id") or m.get("name") or m.get("model") or ""
                    if mid:
                        models.append(str(mid))

    # Format 2: Direct list [ "model1", "model2" ] or [ { "id": "..." } ]
    elif isinstance(data, list):
        for m in data:
            if isinstance(m, str):
                models.append(m)
            elif isinstance(m, dict):
                mid = m.get("id") or m.get("name") or m.get("model") or ""
                if mid:
                    models.append(str(mid))

    # Format 3: { "models": [ ... ] } (some APIs)
    elif isinstance(data, dict) and "models" in data:
        items = data["models"]
        if isinstance(items, list):
            for m in items:
                if isinstance(m, str):
                    models.append(m)
                elif isinstance(m, dict):
                    mid = m.get("id") or m.get("name") or m.get("model") or ""
                    if mid:
                        models.append(str(mid))

    # Format 4: { "object": "list", "data": [...] } with nested model objects
    elif isinstance(data, dict) and data.get("object") == "list":
        for m in data.get("data", []):
            if isinstance(m, dict):
                mid = m.get("id") or m.get("name") or ""
                if mid:
                    models.append(str(mid))

    return sorted(set(models))


async def test_connection(base_url: str, api_key: str, timeout: int = 15,
                          proxy: Optional[str] = None) -> Dict[str, Any]:
    """Test connection to an LLM API endpoint."""
    try:
        models = await fetch_models(base_url, api_key, timeout, proxy)
        return {"success": True, "message": f"连接成功，发现 {len(models)} 个模型",
                "models_count": len(models), "models": models}
    except httpx.ConnectError as e:
        return {"success": False, "message": f"连接失败：无法连接到服务器 ({e})"}
    except httpx.TimeoutException:
        return {"success": False, "message": "连接超时，请检查网络或代理设置"}
    except httpx.HTTPStatusError as e:
        return {"success": False, "message": f"HTTP 错误：{e.response.status_code} - {e.response.text[:200]}"}
    except Exception as e:
        return {"success": False, "message": f"连接测试失败：{str(e)}"}


def _build_chat_url(base_url: str) -> str:
    """Build chat completions URL, handling /v1 suffix correctly."""
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


async def send_chat(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2048,
    top_p: float = 1.0,
    timeout: int = 120,
    proxy: Optional[str] = None,
    thinking_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Send a chat completion request (non-streaming). Returns result dict.
    thinking_mode: None=auto(don't send), 'on'=enable, 'off'=disable."""
    url = _build_chat_url(base_url)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "stream": False,
    }
    # Thinking mode control
    if thinking_mode == "on":
        body["thinking"] = {"type": "enabled"}
    elif thinking_mode == "off":
        body["thinking"] = {"type": "disabled"}
    # None = don't send thinking param (auto/safe default)

    start = time.perf_counter()
    ttfb = 0.0
    async with httpx.AsyncClient(timeout=timeout, proxy=proxy) as client:
        resp = await client.post(url, headers=headers, json=body)
        ttfb = time.perf_counter() - start
        resp.raise_for_status()
        data = resp.json()
    total_time = time.perf_counter() - start
    content = ""
    reasoning = ""
    if "choices" in data and data["choices"]:
        choice = data["choices"][0]
        # Normal message format
        msg = choice.get("message", {})
        # Some LM Studio versions use delta even with stream=false
        if not msg:
            msg = choice.get("delta", {})
        content = msg.get("content", "") or ""
        # Extract reasoning/thinking content (DeepSeek, QwQ, LM Studio, etc.)
        reasoning = msg.get("reasoning_content", "") or msg.get("thinking", "") or ""
        # If content is empty but reasoning exists, use reasoning as content
        # (some models only output to reasoning_content)
        if not content and reasoning:
            content = reasoning
    usage = data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    tokens_per_sec = completion_tokens / total_time if total_time > 0 else 0

    # Estimate thinking time
    thinking_time = round(ttfb, 3) if reasoning else 0

    # If both empty, the response format might be unexpected
    if not content and not reasoning:
        return {
            "success": False,
            "message": f"模型返回空内容 (choices[0] 结构: {json.dumps(data.get('choices', [{}])[0], ensure_ascii=False)[:300]})",
            "content": "",
            "reasoning": "",
            "thinking_time": 0,
            "ttfb": round(ttfb, 3),
            "total_time": round(total_time, 3),
            "tokens_per_sec": 0,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": 0,
        }

    return {
        "success": True,
        "content": content,
        "reasoning": reasoning,
        "thinking_time": thinking_time,
        "ttfb": round(ttfb, 3),
        "total_time": round(total_time, 3),
        "tokens_per_sec": round(tokens_per_sec, 2),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }


async def send_chat_stream(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2048,
    top_p: float = 1.0,
    timeout: int = 120,
    proxy: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream chat completion. Yields delta events and a final summary."""
    url = _build_chat_url(base_url)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "stream": True,
    }
    start = time.perf_counter()
    ttfb = 0.0
    content_parts = []
    reasoning_parts = []
    completion_tokens = 0

    async with httpx.AsyncClient(timeout=timeout, proxy=proxy) as client:
        async with client.stream("POST", url, headers=headers, json=body) as resp:
            resp.raise_for_status()
            first_chunk = True
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if first_chunk:
                    ttfb = time.perf_counter() - start
                    first_chunk = False
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                # Extract reasoning/thinking content
                reasoning_text = delta.get("reasoning_content", "") or delta.get("thinking", "") or ""
                if reasoning_text:
                    reasoning_parts.append(reasoning_text)
                    yield {"type": "reasoning_delta", "content": reasoning_text}
                text = delta.get("content", "") or ""
                if text:
                    content_parts.append(text)
                    completion_tokens += 1
                    yield {"type": "delta", "content": text}

    total_time = time.perf_counter() - start
    full_content = "".join(content_parts)
    full_reasoning = "".join(reasoning_parts)
    tokens_per_sec = completion_tokens / total_time if total_time > 0 else 0
    yield {
        "type": "done",
        "content": full_content,
        "reasoning": full_reasoning,
        "ttfb": round(ttfb, 3),
        "total_time": round(total_time, 3),
        "tokens_per_sec": round(tokens_per_sec, 2),
        "completion_tokens": completion_tokens,
    }
