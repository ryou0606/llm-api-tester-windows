"""
模型配置 CRUD 路由

提供模型配置的增删改查接口，以及测试连接功能。
"""

from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.model_config import ModelConfig
from models.known_model import KnownModel
from adapters.registry import adapter_registry
from smart_parser import parse_smart_paste, get_provider_suggestions

router = APIRouter(prefix="/api/models", tags=["模型配置"])


# ============ Pydantic 请求/响应模型 ============

class ModelConfigCreate(BaseModel):
    """创建模型配置请求"""
    name: str = Field(..., min_length=1, max_length=255, description="模型名称")
    api_type: str = Field(..., description="API 类型: openai_compat / anthropic / gemini 等")
    base_url: str = Field(..., description="API Base URL")
    api_key: str = Field(..., description="API Key")
    model_id: str = Field(..., description="模型 ID")
    context_window: Optional[int] = Field(None, description="上下文窗口大小")
    max_tokens: Optional[int] = Field(None, description="最大输出 token")
    supports_vision: bool = Field(False, description="是否支持图片理解")
    supports_audio: bool = Field(False, description="是否支持语音")


class ModelConfigUpdate(BaseModel):
    """更新模型配置请求（所有字段可选）"""
    name: Optional[str] = Field(None, max_length=255)
    api_type: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_id: Optional[str] = None
    context_window: Optional[int] = None
    max_tokens: Optional[int] = None
    supports_vision: Optional[bool] = None
    supports_audio: Optional[bool] = None
    is_active: Optional[bool] = None


class ModelConfigResponse(BaseModel):
    """模型配置响应"""
    id: int
    name: str
    api_type: str
    base_url: str
    api_key: str  # 前端需要显示（脱敏）
    model_id: str
    context_window: Optional[int]
    max_tokens: Optional[int]
    supports_vision: bool
    supports_audio: bool
    is_active: bool
    status: str
    last_tested_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TestConnectionResponse(BaseModel):
    """测试连接响应"""
    success: bool
    message: str
    latency_ms: Optional[int] = None
    model: Optional[str] = None


class SmartParseRequest(BaseModel):
    """智能粘贴解析请求"""
    text: str = Field(..., min_length=1, description="用户粘贴的原始文本")


class SmartParseResult(BaseModel):
    """单个解析结果"""
    name: str = Field("", description="模型名称")
    api_type: str = Field("openai_compat", description="API 类型")
    base_url: str = Field("", description="API Base URL")
    api_key: str = Field("", description="API Key")
    model_id: str = Field("", description="模型 ID")
    provider: str = Field("", description="检测到的提供商")
    context_window: Optional[int] = Field(None, description="上下文窗口")
    max_tokens: Optional[int] = Field(None, description="最大输出 token")
    supports_vision: bool = Field(False, description="是否支持视觉")
    supports_audio: bool = Field(False, description="是否支持语音")
    notes: str = Field("", description="备注")
    missing_fields: list[str] = Field(default_factory=list, description="缺失的必填字段")


class SmartParseResponse(BaseModel):
    """智能粘贴解析响应"""
    count: int = Field(..., description="解析出的模型数量")
    models: list[SmartParseResult] = Field(..., description="解析结果列表")


class FetchRemoteModelsRequest(BaseModel):
    """拉取远程模型列表请求"""
    base_url: str = Field(..., description="API Base URL")
    api_key: str = Field(..., description="API Key")


class RemoteModel(BaseModel):
    """远程模型信息"""
    id: str = Field(..., description="模型 ID")
    owned_by: str = Field("", description="所有者")
    name: str = Field("", description="显示名称")


class FetchRemoteModelsResponse(BaseModel):
    """拉取远程模型列表响应"""
    success: bool
    models: list[RemoteModel] = Field(default_factory=list)
    message: str = Field("")


# ============ 辅助函数 ============

def mask_api_key(key: str) -> str:
    """对 API Key 进行脱敏处理"""
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


def model_to_response(model: ModelConfig) -> dict:
    """将 ORM 模型转换为响应字典（含 API Key 脱敏）"""
    data = {
        "id": model.id,
        "name": model.name,
        "api_type": model.api_type,
        "base_url": model.base_url,
        "api_key": mask_api_key(model.api_key),
        "model_id": model.model_id,
        "context_window": model.context_window,
        "max_tokens": model.max_tokens,
        "supports_vision": model.supports_vision,
        "supports_audio": model.supports_audio,
        "is_active": model.is_active,
        "status": model.status,
        "last_tested_at": model.last_tested_at,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }
    return data


# ============ 接口 ============

@router.get("", summary="获取所有模型配置")
async def list_models(db: AsyncSession = Depends(get_db)):
    """获取所有模型配置列表"""
    result = await db.execute(
        select(ModelConfig).order_by(ModelConfig.created_at.desc())
    )
    models = result.scalars().all()
    return [model_to_response(m) for m in models]


@router.get("/{model_id}", summary="获取单个模型配置")
async def get_model(model_id: int, db: AsyncSession = Depends(get_db)):
    """根据 ID 获取模型配置"""
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    return model_to_response(model)


@router.get("/meta/api-types", summary="获取支持的 API 类型列表")
async def get_api_types():
    """返回所有支持的 API 类型，供前端下拉选择"""
    return {
        "types": [
            {"value": "openai_compat", "label": "OpenAI 兼容", "description": "覆盖 OpenAI、DeepSeek、Moonshot、智谱、百川等"},
            {"value": "anthropic", "label": "Anthropic (Claude)", "description": "Anthropic 原生 API"},
            {"value": "gemini", "label": "Google Gemini", "description": "Google Gemini API"},
            {"value": "wenxin", "label": "百度文心", "description": "百度文心一言 API"},
            {"value": "tongyi", "label": "阿里通义", "description": "阿里通义千问 API"},
        ]
    }


@router.post("", summary="创建模型配置", status_code=201)
async def create_model(data: ModelConfigCreate, db: AsyncSession = Depends(get_db)):
    """创建新的模型配置"""
    # 验证 API 类型是否支持
    try:
        adapter_registry.get(data.api_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 自动填充上下文窗口（如果用户没填）
    context_window = data.context_window
    if context_window is None:
        result = await db.execute(
            select(KnownModel).where(KnownModel.model_id == data.model_id)
        )
        known = result.scalar_one_or_none()
        if known:
            context_window = known.context_window

    model = ModelConfig(
        name=data.name,
        api_type=data.api_type,
        base_url=data.base_url,
        api_key=data.api_key,
        model_id=data.model_id,
        context_window=context_window,
        max_tokens=data.max_tokens,
        supports_vision=data.supports_vision,
        supports_audio=data.supports_audio,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model_to_response(model)


@router.put("/{model_id}", summary="更新模型配置")
async def update_model(model_id: int, data: ModelConfigUpdate, db: AsyncSession = Depends(get_db)):
    """更新模型配置"""
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    # 只更新传入的字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(model, key, value)

    model.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(model)
    return model_to_response(model)


@router.delete("/{model_id}", summary="删除模型配置")
async def delete_model(model_id: int, db: AsyncSession = Depends(get_db)):
    """删除模型配置"""
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    await db.delete(model)
    await db.commit()
    return {"message": "删除成功"}


@router.post("/{model_id}/test", summary="测试模型连接")
async def test_model_connection(model_id: int, db: AsyncSession = Depends(get_db)):
    """
    测试模型连接是否可用

    发送一个简单的 "Hi" 请求验证 API 配置。
    """
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    # 获取对应的适配器
    try:
        adapter = adapter_registry.get(model.api_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 调用测试连接
    try:
        response = await adapter.test_connection(
            model_id=model.model_id,
            base_url=model.base_url,
            api_key=model.api_key,
        )

        # 更新模型状态
        model.status = "available"
        model.last_tested_at = datetime.now(timezone.utc)
        await db.commit()

        return TestConnectionResponse(
            success=True,
            message="连接成功",
            latency_ms=response.latency_ms,
            model=response.model,
        )
    except Exception as e:
        # 更新模型状态
        model.status = "unavailable"
        model.last_tested_at = datetime.now(timezone.utc)
        await db.commit()

        return TestConnectionResponse(
            success=False,
            message=f"连接失败: {str(e)}",
        )


# ============ 智能粘贴 & 远程模型拉取 ============

@router.post("/parse", summary="智能粘贴解析", response_model=SmartParseResponse)
async def smart_parse(req: SmartParseRequest):
    """
    智能粘贴解析接口

    接收用户粘贴的任意格式文本，自动识别并提取模型配置信息。
    支持 JSON、键值对、自然语言、混合格式。
    支持多模型批量识别（用空行或分隔线区分）。
    """
    results = parse_smart_paste(req.text)
    parsed = []
    for r in results:
        parsed.append(SmartParseResult(
            name=r.name,
            api_type=r.api_type,
            base_url=r.base_url,
            api_key=r.api_key,
            model_id=r.model_id,
            provider=r.provider,
            context_window=r.context_window,
            max_tokens=r.max_tokens,
            supports_vision=r.supports_vision,
            supports_audio=r.supports_audio,
            notes=r.notes,
            missing_fields=r.missing_fields,
        ))
    return SmartParseResponse(count=len(parsed), models=parsed)


@router.post("/fetch-remote-models", summary="拉取远程模型列表", response_model=FetchRemoteModelsResponse)
async def fetch_remote_models(req: FetchRemoteModelsRequest):
    """
    从远程 API 拉取可用模型列表

    调用 {base_url}/models 获取模型列表，兼容 OpenAI 格式。
    """
    url = f"{req.base_url.rstrip('/')}/models"
    headers = {
        "Authorization": f"Bearer {req.api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        models = []
        raw_models = data.get("data", [])

        for m in raw_models:
            model_id = m.get("id", "")
            if not model_id:
                continue
            models.append(RemoteModel(
                id=model_id,
                owned_by=m.get("owned_by", ""),
                name=model_id,
            ))

        # 按 owned_by 分组排序
        models.sort(key=lambda x: (x.owned_by, x.id))

        return FetchRemoteModelsResponse(
            success=True,
            models=models,
            message=f"成功获取 {len(models)} 个模型",
        )
    except httpx.HTTPStatusError as e:
        return FetchRemoteModelsResponse(
            success=False,
            message=f"请求失败 (HTTP {e.response.status_code}): {e.response.text[:200]}",
        )
    except httpx.ConnectError:
        return FetchRemoteModelsResponse(
            success=False,
            message=f"无法连接到 {req.base_url}，请检查网络和地址",
        )
    except Exception as e:
        return FetchRemoteModelsResponse(
            success=False,
            message=f"拉取失败: {str(e)}",
        )


@router.get("/providers", summary="搜索提供商建议")
async def search_providers(q: str = ""):
    """
    根据关键词搜索提供商，返回自动补全建议

    用于前端输入框自动补全 base_url。
    """
    if not q or len(q) < 1:
        return []
    return get_provider_suggestions(q)
