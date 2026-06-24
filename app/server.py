"""FastAPI application definition with static file mounting."""
import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .routes import configs, speed, chatroom, history, roundtable, prompt_templates
from .services import data_store

app = FastAPI(title="LLM API Tester", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(configs.router)
app.include_router(speed.router)
app.include_router(chatroom.router)
app.include_router(history.router)
app.include_router(roundtable.router)
app.include_router(prompt_templates.router)


def _get_static_dir() -> Path:
    """Resolve static directory - supports dev, frozen, and env override."""
    # Environment override (set by main.py for PyInstaller)
    env_dir = os.environ.get("LLM_TESTER_STATIC_DIR")
    if env_dir and Path(env_dir).exists():
        return Path(env_dir)

    # PyInstaller frozen
    if getattr(__import__('sys'), 'frozen', False):
        exe_dir = Path(__import__('sys').executable).parent
        s = exe_dir / "static"
        if s.exists():
            return s
        # Fallback to _MEIPASS
        meipass = Path(__import__('sys')._MEIPASS)
        s = meipass / "static"
        if s.exists():
            return s

    # Dev mode
    return Path(__file__).parent.parent / "static"


# Export endpoints
@app.get("/api/export/all")
async def export_all():
    speed_data = await data_store.read_json("speed_history.json")
    duel_data = await data_store.read_json("duel_history.json")
    debate_data = await data_store.read_json("debate_history.json")
    roundtable_data = await data_store.read_json("roundtable_history.json")
    configs_data = await data_store.read_json("api_configs.json")
    return {
        "configs": configs_data if isinstance(configs_data, list) else [],
        "speed": speed_data if isinstance(speed_data, list) else [],
        "duel": duel_data if isinstance(duel_data, list) else [],
        "debate": debate_data if isinstance(debate_data, list) else [],
        "roundtable": roundtable_data if isinstance(roundtable_data, list) else [],
        "exported_at": datetime.now().isoformat(),
    }


@app.get("/api/export/backup")
async def export_backup():
    """Download all data as a JSON file."""
    speed_data = await data_store.read_json("speed_history.json")
    duel_data = await data_store.read_json("duel_history.json")
    debate_data = await data_store.read_json("debate_history.json")
    roundtable_data = await data_store.read_json("roundtable_history.json")
    configs_data = await data_store.read_json("api_configs.json")
    templates_data = await data_store.read_json("prompt_templates.json")
    backup = {
        "configs": configs_data if isinstance(configs_data, list) else [],
        "speed": speed_data if isinstance(speed_data, list) else [],
        "duel": duel_data if isinstance(duel_data, list) else [],
        "debate": debate_data if isinstance(debate_data, list) else [],
        "roundtable": roundtable_data if isinstance(roundtable_data, list) else [],
        "prompt_templates": templates_data if isinstance(templates_data, list) else [],
        "exported_at": datetime.now().isoformat(),
    }
    filename = f"llm_tester_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return JSONResponse(
        content=backup,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# Mount static files
static_dir = _get_static_dir()
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    index = static_dir / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse(
        status_code=500,
        content={"error": f"static/index.html not found at {static_dir}"}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)[:500], "message": "服务器内部错误"}
    )
