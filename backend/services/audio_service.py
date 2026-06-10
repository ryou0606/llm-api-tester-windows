"""
语音服务 - 处理 STT（语音识别）和 TTS（语音合成）

当前支持 MiMo 语音 API：
- STT: mimo-v2.5-asr
- TTS: mimo-v2.5-tts / mimo-v2.5-tts-voicedesign / mimo-v2.5-tts-voiceclone
"""

import json
import logging
import base64
import httpx

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 60.0

# MiMo 预置音色列表
MIMO_VOICES = [
    {"id": "冰糖", "name": "冰糖", "language": "中文", "gender": "女", "models": ["mimo-v2.5-tts"]},
    {"id": "茉莉", "name": "茉莉", "language": "中文", "gender": "女", "models": ["mimo-v2.5-tts"]},
    {"id": "苏打", "name": "苏打", "language": "中文", "gender": "男", "models": ["mimo-v2.5-tts"]},
    {"id": "白桦", "name": "白桦", "language": "中文", "gender": "男", "models": ["mimo-v2.5-tts"]},
    {"id": "Mia", "name": "Mia", "language": "英文", "gender": "女", "models": ["mimo-v2.5-tts"]},
    {"id": "Chloe", "name": "Chloe", "language": "英文", "gender": "女", "models": ["mimo-v2.5-tts"]},
    {"id": "Milo", "name": "Milo", "language": "英文", "gender": "男", "models": ["mimo-v2.5-tts"]},
    {"id": "Dean", "name": "Dean", "language": "英文", "gender": "男", "models": ["mimo-v2.5-tts"]},
    {"id": "mimo_default", "name": "默认", "language": "通用", "gender": "通用", "models": ["mimo-v2-tts", "mimo-v2.5-tts"]},
    {"id": "default_zh", "name": "中文默认", "language": "中文", "gender": "通用", "models": ["mimo-v2-tts"]},
    {"id": "default_en", "name": "英文默认", "language": "英文", "gender": "通用", "models": ["mimo-v2-tts"]},
]

# MiMo TTS 模型列表
MIMO_TTS_MODELS = [
    {"id": "mimo-v2.5-tts", "name": "预置音色合成", "description": "使用内置精品音色"},
    {"id": "mimo-v2.5-tts-voicedesign", "name": "文字描述定制音色", "description": "自然语言描述自动生成音色"},
    {"id": "mimo-v2.5-tts-voiceclone", "name": "音频样本克隆音色", "description": "上传音频样本克隆音色"},
]

# 常用风格快捷选项
STYLE_PRESETS = [
    {"id": "温柔", "label": "温柔", "prompt": "用温柔的语调朗读"},
    {"id": "活泼", "label": "活泼", "prompt": "用活泼上扬的语调朗读"},
    {"id": "严肃", "label": "严肃", "prompt": "用严肃正式的语调朗读"},
    {"id": "东北话", "label": "东北话", "prompt": "用东北方言朗读"},
    {"id": "粤语", "label": "粤语", "prompt": "用粤语朗读"},
    {"id": "播音", "label": "播音", "prompt": "用播音腔朗读"},
    {"id": "讲故事", "label": "讲故事", "prompt": "用讲故事的语气朗读"},
]


class AudioService:
    """语音服务"""

    async def stt(
        self,
        audio_base64: str,
        api_key: str,
        model_id: str = "mimo-v2.5-asr",
        base_url: str = "https://api.xiaomimimo.com/v1",
        language: str = "auto",
    ) -> dict:
        """
        语音识别（STT）

        Args:
            audio_base64: Base64 编码的音频数据
            api_key: API Key
            model_id: 模型 ID
            base_url: API Base URL
            language: 语言 (auto/zh/en)

        Returns:
            {"text": "识别结果", "duration": 秒数}
        """
        url = f"{base_url.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": f"data:audio/wav;base64,{audio_base64}",
                                "format": "wav",
                            },
                        },
                    ],
                }
            ],
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        # 解析响应
        content = ""
        if data.get("choices"):
            content = data["choices"][0].get("message", {}).get("content", "")

        duration = 0
        if data.get("usage"):
            duration = data["usage"].get("seconds", 0)

        return {"text": content, "duration": duration}

    async def tts(
        self,
        text: str,
        api_key: str,
        voice: str = "冰糖",
        model_id: str = "mimo-v2.5-tts",
        base_url: str = "https://api.xiaomimimo.com/v1",
        style_prompt: str | None = None,
    ) -> dict:
        """
        语音合成（TTS）

        Args:
            text: 要合成的文本
            api_key: API Key
            voice: 音色 ID
            model_id: 模型 ID
            base_url: API Base URL
            style_prompt: 风格控制指令

        Returns:
            {"audio_base64": "Base64 音频", "format": "wav"}
        """
        url = f"{base_url.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # 构建消息
        messages = []

        # user message: 风格控制（可选）
        if style_prompt:
            messages.append({
                "role": "user",
                "content": style_prompt,
            })

        # assistant message: 目标文本
        messages.append({
            "role": "assistant",
            "content": text,
        })

        payload = {
            "model": model_id,
            "messages": messages,
            "stream": False,
            "audio": {
                "format": "wav",
                "voice": voice,
            },
        }

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        # 解析音频数据
        audio_base64 = ""
        if data.get("choices"):
            audio_data = data["choices"][0].get("message", {}).get("audio", {})
            if isinstance(audio_data, dict):
                audio_base64 = audio_data.get("data", "")
            elif isinstance(audio_data, str):
                audio_base64 = audio_data

        return {"audio_base64": audio_base64, "format": "wav"}

    def get_voices(self) -> list[dict]:
        """获取可用音色列表"""
        return MIMO_VOICES

    def get_tts_models(self) -> list[dict]:
        """获取 TTS 模型列表"""
        return MIMO_TTS_MODELS

    def get_style_presets(self) -> list[dict]:
        """获取风格预设列表"""
        return STYLE_PRESETS


# 全局单例
audio_service = AudioService()
