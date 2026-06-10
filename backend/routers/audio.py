"""
语音路由 - 提供 STT（语音识别）和 TTS（语音合成）接口

MiMo 语音 API 优先，同时支持配置其他模型。
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.model_config import ModelConfig
from services.audio_service import audio_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio", tags=["语音"])


# ============ Pydantic 请求/响应模型 ============

class TTSByModelRequest(BaseModel):
    """通过模型配置 ID 调用 TTS"""
    text: str = Field(..., min_length=1, description="要合成的文本")
    model_config_id: int = Field(..., description="模型配置 ID")
    voice: str = Field("冰糖", description="音色 ID")
    style_prompt: str | None = Field(None, description="风格控制指令")


class STTRequest(BaseModel):
    """语音识别请求"""
    audio_data: str = Field(..., description="Base64 编码的音频数据")
    model_id: str = Field("mimo-v2.5-asr", description="模型 ID")
    base_url: str = Field("https://api.xiaomimimo.com/v1", description="API Base URL")
    api_key: str = Field(..., description="API Key")
    language: str = Field("auto", description="语言: auto/zh/en")


class TTSRequest(BaseModel):
    """语音合成请求"""
    text: str = Field(..., min_length=1, description="要合成的文本")
    voice: str = Field("冰糖", description="音色 ID")
    model_id: str = Field("mimo-v2.5-tts", description="TTS 模型 ID")
    base_url: str = Field("https://api.xiaomimimo.com/v1", description="API Base URL")
    api_key: str = Field(..., description="API Key")
    style_prompt: str | None = Field(None, description="风格控制指令")


# ============ 接口 ============

@router.post("/stt", summary="语音识别")
async def speech_to_text(data: STTRequest):
    """
    将音频转为文字（STT）

    支持 MiMo mimo-v2.5-asr 模型，也支持其他 OpenAI 兼容的 STT 模型。
    """
    try:
        result = await audio_service.stt(
            audio_base64=data.audio_data,
            api_key=data.api_key,
            model_id=data.model_id,
            base_url=data.base_url,
            language=data.language,
        )
        return result
    except Exception as e:
        logger.error(f"STT 失败: {e}")
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")


@router.post("/tts", summary="语音合成")
async def text_to_speech(data: TTSRequest):
    """
    将文字转为语音（TTS）

    支持 MiMo mimo-v2.5-tts 系列模型。返回 WAV 音频二进制。
    """
    try:
        result = await audio_service.tts(
            text=data.text,
            api_key=data.api_key,
            voice=data.voice,
            model_id=data.model_id,
            base_url=data.base_url,
            style_prompt=data.style_prompt,
        )

        if not result.get("audio_base64"):
            raise HTTPException(status_code=500, detail="TTS 未返回音频数据")

        audio_bytes = __import__("base64").b64decode(result["audio_base64"])
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=tts_output.wav"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS 失败: {e}")
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")


@router.post("/tts-by-model", summary="通过模型配置 ID 语音合成")
async def text_to_speech_by_model(data: TTSByModelRequest, db: AsyncSession = Depends(get_db)):
    """
    通过已保存的模型配置 ID 调用 TTS

    前端无需知道 API Key，后端从数据库读取。
    """
    # 查找模型配置
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == data.model_config_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")

    try:
        tts_result = await audio_service.tts(
            text=data.text,
            api_key=model.api_key,
            voice=data.voice,
            model_id=model.model_id,
            base_url=model.base_url,
            style_prompt=data.style_prompt,
        )

        if not tts_result.get("audio_base64"):
            raise HTTPException(status_code=500, detail="TTS 未返回音频数据")

        audio_bytes = __import__("base64").b64decode(tts_result["audio_base64"])
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=tts_output.wav"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS 失败: {e}")
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")


@router.get("/voices", summary="获取可用音色列表")
async def get_voices():
    """获取所有可用的 TTS 音色"""
    return {"voices": audio_service.get_voices()}


@router.get("/tts-models", summary="获取 TTS 模型列表")
async def get_tts_models():
    """获取所有可用的 TTS 模型"""
    return {"models": audio_service.get_tts_models()}


@router.get("/style-presets", summary="获取风格预设列表")
async def get_style_presets():
    """获取 TTS 风格预设（快捷按钮用）"""
    return {"presets": audio_service.get_style_presets()}
