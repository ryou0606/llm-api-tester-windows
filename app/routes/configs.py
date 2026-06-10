"""API configuration CRUD routes."""
import uuid
from fastapi import APIRouter, HTTPException

from ..models import APIConfigCreate, APIConfigUpdate, FetchModelsRequest, TestConnectionRequest
from ..services import data_store, llm_client

router = APIRouter(prefix="/api", tags=["configs"])


@router.get("/configs")
async def list_configs():
    configs = await data_store.read_json("api_configs.json")
    return configs


@router.post("/configs")
async def create_config(config: APIConfigCreate):
    configs = await data_store.read_json("api_configs.json")
    if not isinstance(configs, list):
        configs = []
    new_config = {
        "id": str(uuid.uuid4()),
        "name": config.name,
        "base_url": config.base_url,
        "api_key": config.api_key,
        "enabled": config.enabled,
        "models": config.models,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "timeout": config.timeout,
        "proxy": config.proxy,
    }
    configs.append(new_config)
    await data_store.write_json("api_configs.json", configs)
    return new_config


@router.put("/configs/{config_id}")
async def update_config(config_id: str, update: APIConfigUpdate):
    configs = await data_store.read_json("api_configs.json")
    if not isinstance(configs, list):
        configs = []
    for cfg in configs:
        if cfg["id"] == config_id:
            update_data = update.model_dump(exclude_unset=True)
            cfg.update(update_data)
            await data_store.write_json("api_configs.json", configs)
            return cfg
    raise HTTPException(status_code=404, detail="配置不存在")


@router.delete("/configs/{config_id}")
async def delete_config(config_id: str):
    configs = await data_store.read_json("api_configs.json")
    if not isinstance(configs, list):
        configs = []
    new_configs = [c for c in configs if c.get("id") != config_id]
    if len(new_configs) == len(configs):
        raise HTTPException(status_code=404, detail="配置不存在")
    await data_store.write_json("api_configs.json", new_configs)
    return {"success": True}


@router.post("/configs/check")
async def check_all_configs():
    """Check connectivity for all enabled configs."""
    configs = await data_store.read_json("api_configs.json")
    if not isinstance(configs, list):
        configs = []
    results = []
    for cfg in configs:
        if not cfg.get("enabled", True):
            results.append({"id": cfg["id"], "name": cfg.get("name", ""), "status": "disabled"})
            continue
        try:
            res = await llm_client.test_connection(
                cfg["base_url"], cfg.get("api_key", ""), cfg.get("timeout", 30), cfg.get("proxy"))
            results.append({"id": cfg["id"], "name": cfg.get("name", ""),
                            "status": "ok" if res["success"] else "fail", "message": res["message"]})
        except Exception as e:
            results.append({"id": cfg["id"], "name": cfg.get("name", ""), "status": "fail", "message": str(e)[:200]})
    return results


@router.get("/combos")
async def get_combos():
    """Get enabled configs with their models for selection."""
    configs = await data_store.read_json("api_configs.json")
    if not isinstance(configs, list):
        configs = []
    combos = []
    for cfg in configs:
        if not cfg.get("enabled", True):
            continue
        for model in cfg.get("models", []):
            combos.append({
                "config_id": cfg["id"],
                "config_name": cfg.get("name", ""),
                "model": model,
                "label": f"{cfg.get('name', '')} / {model}",
            })
    return combos


@router.post("/fetch-models")
async def fetch_models(req: FetchModelsRequest):
    try:
        models = await llm_client.fetch_models(req.base_url, req.api_key, req.timeout, req.proxy)
        return {"success": True, "models": models}
    except Exception as e:
        return {"success": False, "message": str(e)[:300]}


@router.post("/test-connection")
async def test_connection(req: TestConnectionRequest):
    return await llm_client.test_connection(req.base_url, req.api_key, req.timeout, req.proxy)
