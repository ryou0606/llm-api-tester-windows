"""JSON file-based data store with thread-safe read/write."""
import json
import os
import asyncio
from pathlib import Path
from typing import Any

_lock = asyncio.Lock()


def _get_data_dir() -> Path:
    """Get the data directory, creating it if needed."""
    if os.environ.get("LLM_TESTER_DATA_DIR"):
        d = Path(os.environ["LLM_TESTER_DATA_DIR"])
    else:
        d = Path(__file__).resolve().parent.parent.parent / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


async def read_json(filename: str) -> Any:
    """Read a JSON file from the data directory."""
    async with _lock:
        path = _get_data_dir() / filename
        if not path.exists():
            return [] if filename.endswith(".json") else {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return [] if filename.endswith(".json") else {}


async def write_json(filename: str, data: Any) -> None:
    """Write data to a JSON file in the data directory."""
    async with _lock:
        path = _get_data_dir() / filename
        tmp = path.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp.replace(path)
        except Exception:
            if tmp.exists():
                tmp.unlink()
            raise


def get_data_dir() -> Path:
    """Return the data directory path."""
    return _get_data_dir()
