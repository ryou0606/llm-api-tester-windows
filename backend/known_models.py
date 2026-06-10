"""
已知模型上下文窗口数据
用于自动填充模型的上下文窗口大小

数据来源：各厂商官方文档
最后更新：2026-06-03
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.known_model import KnownModel


# 内置已知模型数据，用于初始化数据库
KNOWN_MODELS_DATA = [
    # MiMo 系列
    {"model_id": "mimo-v2.5-pro", "context_window": 1048576, "provider": "Xiaomi"},
    {"model_id": "mimo-v2-omni", "context_window": 262144, "provider": "Xiaomi"},
    {"model_id": "mimo-v2.5-asr", "context_window": 0, "provider": "Xiaomi"},
    {"model_id": "mimo-v2.5-tts", "context_window": 0, "provider": "Xiaomi"},
    # OpenAI
    {"model_id": "gpt-4o", "context_window": 128000, "provider": "OpenAI"},
    {"model_id": "gpt-4o-mini", "context_window": 128000, "provider": "OpenAI"},
    {"model_id": "gpt-4-turbo", "context_window": 128000, "provider": "OpenAI"},
    {"model_id": "gpt-4", "context_window": 8192, "provider": "OpenAI"},
    {"model_id": "gpt-3.5-turbo", "context_window": 16385, "provider": "OpenAI"},
    {"model_id": "o1", "context_window": 200000, "provider": "OpenAI"},
    {"model_id": "o1-mini", "context_window": 128000, "provider": "OpenAI"},
    {"model_id": "o3", "context_window": 200000, "provider": "OpenAI"},
    {"model_id": "o3-mini", "context_window": 200000, "provider": "OpenAI"},
    {"model_id": "o4-mini", "context_window": 200000, "provider": "OpenAI"},
    {"model_id": "gpt-4.1", "context_window": 1047576, "provider": "OpenAI"},
    {"model_id": "gpt-4.1-mini", "context_window": 1047576, "provider": "OpenAI"},
    {"model_id": "gpt-4.1-nano", "context_window": 1047576, "provider": "OpenAI"},
    # Anthropic
    {"model_id": "claude-sonnet-4-20250514", "context_window": 200000, "provider": "Anthropic"},
    {"model_id": "claude-3.5-sonnet", "context_window": 200000, "provider": "Anthropic"},
    {"model_id": "claude-3.5-haiku", "context_window": 200000, "provider": "Anthropic"},
    {"model_id": "claude-3-opus", "context_window": 200000, "provider": "Anthropic"},
    {"model_id": "claude-3-sonnet", "context_window": 200000, "provider": "Anthropic"},
    {"model_id": "claude-3-haiku", "context_window": 200000, "provider": "Anthropic"},
    # DeepSeek
    {"model_id": "deepseek-chat", "context_window": 64000, "provider": "DeepSeek"},
    {"model_id": "deepseek-coder", "context_window": 64000, "provider": "DeepSeek"},
    {"model_id": "deepseek-reasoner", "context_window": 64000, "provider": "DeepSeek"},
    # Google Gemini
    {"model_id": "gemini-2.5-pro", "context_window": 1048576, "provider": "Google"},
    {"model_id": "gemini-2.5-flash", "context_window": 1048576, "provider": "Google"},
    {"model_id": "gemini-2.0-flash", "context_window": 1048576, "provider": "Google"},
    {"model_id": "gemini-2.0-flash-lite", "context_window": 1048576, "provider": "Google"},
    {"model_id": "gemini-1.5-pro", "context_window": 2097152, "provider": "Google"},
    {"model_id": "gemini-1.5-flash", "context_window": 1048576, "provider": "Google"},
    {"model_id": "gemini-pro", "context_window": 32768, "provider": "Google"},
    # 智谱 GLM
    {"model_id": "glm-4-plus", "context_window": 128000, "provider": "Zhipu"},
    {"model_id": "glm-4", "context_window": 128000, "provider": "Zhipu"},
    {"model_id": "glm-4-flash", "context_window": 128000, "provider": "Zhipu"},
    {"model_id": "glm-4-long", "context_window": 1048576, "provider": "Zhipu"},
    {"model_id": "glm-4v", "context_window": 2048, "provider": "Zhipu"},
    {"model_id": "glm-4v-plus", "context_window": 8192, "provider": "Zhipu"},
    # 通义千问
    {"model_id": "qwen-turbo", "context_window": 131072, "provider": "Alibaba"},
    {"model_id": "qwen-plus", "context_window": 131072, "provider": "Alibaba"},
    {"model_id": "qwen-max", "context_window": 32768, "provider": "Alibaba"},
    {"model_id": "qwen-long", "context_window": 10000000, "provider": "Alibaba"},
    {"model_id": "qwen-vl-plus", "context_window": 131072, "provider": "Alibaba"},
    {"model_id": "qwen-vl-max", "context_window": 32768, "provider": "Alibaba"},
    {"model_id": "qwen2.5-72b-instruct", "context_window": 32768, "provider": "Alibaba"},
    {"model_id": "qwen3-235b-a22b", "context_window": 131072, "provider": "Alibaba"},
    # Moonshot (Kimi)
    {"model_id": "moonshot-v1-8k", "context_window": 8192, "provider": "Moonshot"},
    {"model_id": "moonshot-v1-32k", "context_window": 32768, "provider": "Moonshot"},
    {"model_id": "moonshot-v1-128k", "context_window": 131072, "provider": "Moonshot"},
    # 百川
    {"model_id": "baichuan4", "context_window": 32768, "provider": "Baichuan"},
    {"model_id": "Baichuan4-Turbo", "context_window": 32768, "provider": "Baichuan"},
    # MiniMax
    {"model_id": "abab6.5-chat", "context_window": 245760, "provider": "MiniMax"},
    {"model_id": "abab6.5s-chat", "context_window": 245760, "provider": "MiniMax"},
    {"model_id": "MiniMax-Text-01", "context_window": 1000000, "provider": "MiniMax"},
    # 零一万物
    {"model_id": "yi-large", "context_window": 32768, "provider": "01.AI"},
    {"model_id": "yi-medium", "context_window": 16384, "provider": "01.AI"},
    {"model_id": "yi-large-turbo", "context_window": 32768, "provider": "01.AI"},
    # 阶跃星辰
    {"model_id": "step-1-8k", "context_window": 8192, "provider": "StepFun"},
    {"model_id": "step-1-32k", "context_window": 32768, "provider": "StepFun"},
    {"model_id": "step-1-128k", "context_window": 131072, "provider": "StepFun"},
    {"model_id": "step-1v-8k", "context_window": 8192, "provider": "StepFun"},
    # Groq
    {"model_id": "llama-3.3-70b-versatile", "context_window": 128000, "provider": "Groq"},
    {"model_id": "llama-3.1-8b-instant", "context_window": 128000, "provider": "Groq"},
    {"model_id": "mixtral-8x7b-32768", "context_window": 32768, "provider": "Groq"},
    {"model_id": "gemma2-9b-it", "context_window": 8192, "provider": "Groq"},
    # SiliconFlow
    {"model_id": "deepseek-ai/DeepSeek-V3", "context_window": 65536, "provider": "SiliconFlow"},
    {"model_id": "deepseek-ai/DeepSeek-R1", "context_window": 65536, "provider": "SiliconFlow"},
    {"model_id": "Qwen/Qwen2.5-72B-Instruct", "context_window": 32768, "provider": "SiliconFlow"},
    # OpenRouter (常用模型)
    {"model_id": "openai/gpt-4o", "context_window": 128000, "provider": "OpenRouter"},
    {"model_id": "anthropic/claude-3.5-sonnet", "context_window": 200000, "provider": "OpenRouter"},
    {"model_id": "google/gemini-2.0-flash", "context_window": 1048576, "provider": "OpenRouter"},
    {"model_id": "deepseek/deepseek-chat", "context_window": 64000, "provider": "OpenRouter"},
    # Fireworks
    {"model_id": "accounts/fireworks/models/llama-v3p3-70b-instruct", "context_window": 131072, "provider": "Fireworks"},
    {"model_id": "accounts/fireworks/models/deepseek-v3", "context_window": 131072, "provider": "Fireworks"},
]


async def seed_known_models(session: AsyncSession):
    """初始化已知模型数据（如果表为空）"""
    result = await session.execute(select(func.count(KnownModel.id)))
    count = result.scalar()

    if count == 0:
        for data in KNOWN_MODELS_DATA:
            model = KnownModel(**data)
            session.add(model)
        await session.commit()
