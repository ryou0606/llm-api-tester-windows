"""
智能粘贴解析引擎 v2

通过多策略级联解析，从任意格式文本中提取模型配置信息。
支持：JSON、键值对、自然语言、混合格式。
不依赖外部 LLM，纯规则引擎。
"""

import re
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedModel:
    """解析出的单个模型配置"""
    name: str = ""
    api_type: str = "openai_compat"
    base_url: str = ""
    api_key: str = ""
    model_id: str = ""
    provider: str = ""
    context_window: Optional[int] = None
    max_tokens: Optional[int] = None
    supports_vision: bool = False
    supports_audio: bool = False
    notes: str = ""
    missing_fields: list[str] = field(default_factory=list)


# ============ 提供商数据库 ============

PROVIDER_DB = [
    (["openai", "gpt", "chatgpt"], "OpenAI", "https://api.openai.com/v1", "openai_compat"),
    (["deepseek", "深度求索", "ds"], "DeepSeek", "https://api.deepseek.com/v1", "openai_compat"),
    (["zhipu", "glm", "智谱", "chatglm"], "智谱 GLM", "https://open.bigmodel.cn/api/paas/v4", "openai_compat"),
    (["moonshot", "kimi", "月之暗面"], "Moonshot", "https://api.moonshot.cn/v1", "openai_compat"),
    (["qwen", "通义", "千问", "dashscope", "百炼"], "阿里通义", "https://dashscope.aliyuncs.com/compatible-mode/v1", "openai_compat"),
    (["doubao", "豆包", "火山", "volces", "ark", "seed"], "火山引擎", "https://ark.cn-beijing.volces.com/api/v3", "openai_compat"),
    (["ernie", "文心", "千帆", "qianfan"], "百度文心", "https://qianfan.baidubce.com/v2", "openai_compat"),
    (["spark", "星火", "讯飞", "xfyun"], "科大讯飞", "https://spark-api-open.xf-yun.com/v1", "openai_compat"),
    (["hunyuan", "混元", "腾讯"], "腾讯混元", "https://cloud.tencent.com/api/hy/v1", "openai_compat"),
    (["minimax", "abab"], "MiniMax", "https://api.minimaxi.com/v1", "openai_compat"),
    (["baichuan", "百川"], "百川", "https://api.baichuan-ai.com/v1", "openai_compat"),
    (["mimo", "小米"], "MiMo", "https://api.xiaomimimo.com/v1", "openai_compat"),
    (["ollama"], "Ollama", "http://localhost:11434/v1", "openai_compat"),
    (["anthropic", "claude"], "Anthropic", "", "openai_compat"),
    (["gemini", "google"], "Google Gemini", "https://generativelanguage.googleapis.com/v1", "openai_compat"),
    (["openrouter"], "OpenRouter", "https://openrouter.ai/api/v1", "openai_compat"),
    (["siliconflow", "硅基流动"], "SiliconFlow", "https://api.siliconflow.cn/v1", "openai_compat"),
    (["together"], "Together AI", "https://api.together.xyz/v1", "openai_compat"),
    (["groq"], "Groq", "https://api.groq.com/openai/v1", "openai_compat"),
    (["fireworks"], "Fireworks", "https://api.fireworks.ai/inference/v1", "openai_compat"),
    (["yi", "零一", "lingyiwanwu"], "零一万物", "https://api.lingyiwanwu.com/v1", "openai_compat"),
    (["step", "阶跃"], "阶跃星辰", "https://api.stepfun.com/v1", "openai_compat"),
    (["cloudflare", "cf"], "Cloudflare", "https://api.cloudflare.com/client/v4", "openai_compat"),
]

# 模型 ID 前缀 → 提供商
MODEL_ID_PREFIXES = {
    "gpt-": "OpenAI", "o1-": "OpenAI", "o3-": "OpenAI", "o4-": "OpenAI", "chatgpt-": "OpenAI",
    "deepseek-": "DeepSeek",
    "glm-": "智谱 GLM",
    "moonshot-": "Moonshot", "kimi-": "Moonshot",
    "qwen-": "阿里通义",
    "doubao-": "火山引擎",
    "ernie-": "百度文心",
    "spark-": "科大讯飞",
    "hunyuan-": "腾讯混元",
    "abab-": "MiniMax",
    "baichuan": "百川",
    "mimo-": "MiMo",
    "claude-": "Anthropic",
    "gemini-": "Google Gemini",
    "yi-": "零一万物",
    "step-": "阶跃星辰",
}

# Key 前缀
KEY_PATTERNS = [
    (r"sk-ant-", "Anthropic"),
    (r"sk-or-v1-", "OpenRouter"),
    (r"sk-", None),
    (r"tp-", "MiMo"),
    (r"cfut_", "Cloudflare"),
]

VISION_KEYWORDS = ["vision", "视觉", "图片", "多模态", "multimodal", "vl", "omni"]
AUDIO_KEYWORDS = ["audio", "语音", "tts", "stt", "asr", "whisper", "语音识别", "语音合成"]


# ============ 工具函数 ============

def _extract_urls(text: str) -> list[str]:
    """提取所有 URL"""
    pattern = r'https?://[^\s<>"\')\]，。、；：）】}]+'
    urls = re.findall(pattern, text)
    return [u.rstrip('.,;:，。、；：') for u in urls]


def _extract_keys(text: str) -> list[tuple[str, Optional[str]]]:
    """提取 API Key"""
    results = []
    key_pattern = r'(sk-[a-zA-Z0-9_-]{8,}|tp-[a-zA-Z0-9_-]{8,}|cfut_[a-zA-Z0-9_-]{8,})'
    for match in re.finditer(key_pattern, text):
        key = match.group(1)
        provider_hint = None
        for prefix, prov in KEY_PATTERNS:
            if key.startswith(prefix):
                provider_hint = prov
                break
        results.append((key, provider_hint))
    # 智谱格式
    zhipu_pattern = r'([a-f0-9]{32}\.[a-zA-Z0-9]{24,})'
    for match in re.finditer(zhipu_pattern, text):
        results.append((match.group(1), "智谱 GLM"))
    return results


def _extract_model_ids(text: str) -> list[str]:
    """提取可能的模型 ID"""
    models = set()
    for prefix in MODEL_ID_PREFIXES:
        pattern = rf'\b{re.escape(prefix)}[a-zA-Z0-9._:-]+'
        for match in re.finditer(pattern, text, re.IGNORECASE):
            models.add(match.group(0).lower())
    # Ollama 格式
    ollama_pattern = r'\b([a-zA-Z][a-zA-Z0-9._-]+:\d+[bB])\b'
    for match in re.finditer(ollama_pattern, text):
        models.add(match.group(1).lower())
    return sorted(models)


def _is_url(s: str) -> bool:
    """判断是否像 URL"""
    s = s.strip().strip('"').strip("'")
    return s.startswith("http://") or s.startswith("https://")


def _looks_like_model_id(s: str) -> bool:
    """判断是否像模型 ID（排除纯中文、数字+量词、描述性文本等）"""
    s = s.strip()
    if not s:
        return False
    # 纯中文 → 不是
    if re.match(r'^[\u4e00-\u9fff\s]+$', s):
        return False
    # 数字+中文量词（如 "352 个"、"214 个"）→ 不是
    if re.match(r'^[\d\s]+[个种条块台套只]', s):
        return False
    # 中文开头+数字+中文（如 "总计 352 个"）→ 不是
    if re.match(r'^[\u4e00-\u9fff]', s) and re.search(r'[\u4e00-\u9fff]', s[1:]):
        return False
    # 纯数字 → 不是
    if re.match(r'^\d+$', s):
        return False
    # 包含英文字母 → 很可能是模型 ID
    if re.search(r'[a-zA-Z]', s):
        return True
    # 数字+英文标点（如 "7b"、"14b"）→ 可能是
    if re.match(r'^\d+[bB]$', s):
        return True
    return False


def _clean_value(v: str) -> str:
    """清理值"""
    v = v.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
    v = v.rstrip(',，')
    return v.strip()


def _clean_url_value(v: str) -> str:
    """清理 URL 值"""
    v = v.strip().strip('"').strip("'")
    v = re.sub(r'[，。、；：）】\s].*$', '', v)
    v = v.rstrip('.,;:')
    return v


def _detect_provider_from_url(url: str) -> tuple[str, str]:
    """从 URL 检测提供商"""
    url_lower = url.lower()
    for keywords, provider, default_url, _ in PROVIDER_DB:
        for kw in keywords:
            if kw in url_lower:
                return provider, default_url
    return "", ""


def _detect_provider_from_text(text: str) -> tuple[str, str]:
    """从文本关键词检测提供商（短关键词用词边界匹配）"""
    text_lower = text.lower()
    for keywords, provider, default_url, _ in PROVIDER_DB:
        for kw in keywords:
            # 短关键词（<=3字符）用词边界匹配，避免子串误匹配
            if len(kw) <= 3:
                pattern = rf'\b{re.escape(kw)}\b'
                if re.search(pattern, text_lower):
                    return provider, default_url
            else:
                if kw in text_lower:
                    return provider, default_url
    return "", ""


def _detect_provider_from_model(model_id: str) -> tuple[str, str]:
    """从模型 ID 前缀检测提供商"""
    mid = model_id.lower()
    for prefix, provider in MODEL_ID_PREFIXES.items():
        if mid.startswith(prefix):
            for keywords, prov, default_url, _ in PROVIDER_DB:
                if prov == provider:
                    return provider, default_url
            return provider, ""
    return "", ""


def _fill_missing(model: ParsedModel) -> ParsedModel:
    """标记缺失的必填字段"""
    model.missing_fields = []
    if not model.name:
        model.missing_fields.append("name")
    if not model.base_url:
        model.missing_fields.append("base_url")
    if not model.api_key:
        model.missing_fields.append("api_key")
    if not model.model_id:
        model.missing_fields.append("model_id")
    return model


# ============ 核心解析 ============

# 中文标签 → 字段名
LABEL_MAP = {
    "接口地址": "base_url", "接口": "base_url", "url": "base_url",
    "地址": "base_url", "base_url": "base_url", "base url": "base_url",
    "baseurl": "base_url", "endpoint": "base_url", "api url": "base_url",
    "api_key": "api_key", "apikey": "api_key", "api key": "api_key",
    "密钥": "api_key", "key": "api_key", "token": "api_key",
    "密钥串": "api_key", "secret": "api_key", "bearer_token": "api_key",
    "密钥①": "api_key", "密钥②": "api_key", "备用标识": "api_key",
    "模型接口": "model_id", "模型名称": "model_id", "模型名": "model_id",
    "模型": "model_id", "model": "model_id", "model_id": "model_id",
    "可用模型": "model_id", "模型id": "model_id", "模型 id": "model_id",
    "官方模型": "model_id", "标准模型": "model_id",
    "名称": "name", "name": "name", "厂商": "name",
    "标识": "name", "model_provider": "name",
    "状态": "notes", "status": "notes", "备注": "notes", "用途": "notes",
}

# 这些标签的值不可能是 URL（避免 "模型接口：xxx" 被当成 URL）
NON_URL_LABELS = {"模型接口", "模型名称", "模型名", "模型", "model", "model_id",
                  "可用模型", "名称", "name", "厂商", "标识", "model_provider",
                  "状态", "status", "备注", "用途"}


def _extract_kv_pairs(text: str) -> dict:
    """从文本中提取键值对"""
    kv = {}

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 去掉编号前缀
        line = re.sub(r'^\d+[\.\)、]\s*', '', line)

        matched = False
        # 优先全角冒号
        for sep in ["：", "="]:
            if sep in line:
                parts = line.split(sep, 1)
                if len(parts) == 2:
                    key_part = parts[0].strip().lower()
                    raw_val = parts[1]

                    for label, field_name in LABEL_MAP.items():
                        if label in key_part:
                            if field_name not in kv or not kv[field_name]:
                                # 判断该标签是否可能是 URL
                                is_url_label = label not in NON_URL_LABELS and field_name == "base_url"
                                if is_url_label and _is_url(raw_val):
                                    kv[field_name] = _clean_url_value(raw_val)
                                elif field_name == "base_url" and not _is_url(raw_val):
                                    # 标签暗示 URL 但值不像 URL，可能是模型 ID 之类
                                    # 只有当值真的是 URL 时才填入
                                    pass
                                else:
                                    kv[field_name] = _clean_value(raw_val)
                            matched = True
                            break
                if matched:
                    break

        # 半角冒号（更严格的匹配）
        if not matched and ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                key_part = parts[0].strip().lower()
                raw_val = parts[1].strip()
                if raw_val.startswith("//"):
                    continue
                for label, field_name in LABEL_MAP.items():
                    if label in key_part:
                        if field_name not in kv or not kv[field_name]:
                            is_url_label = label not in NON_URL_LABELS and field_name == "base_url"
                            if is_url_label and _is_url(raw_val):
                                kv[field_name] = _clean_url_value(raw_val)
                            elif field_name == "base_url" and not _is_url(raw_val):
                                pass
                            else:
                                kv[field_name] = _clean_value(raw_val)
                        matched = True
                        break

        # 空格分隔（如 "密钥 sk-xxx"、"模型 gpt-4o"）
        if not matched:
            for label, field_name in LABEL_MAP.items():
                # 只匹配短标签，避免误匹配
                pattern = rf'^{re.escape(label)}\s+(\S+)'
                m = re.match(pattern, line, re.IGNORECASE)
                if m:
                    val = _clean_value(m.group(1))
                    if field_name not in kv or not kv[field_name]:
                        if field_name == "base_url" and not _is_url(val):
                            pass
                        else:
                            kv[field_name] = val
                    matched = True
                    break

        # 特殊格式：xxx模型 xxx（如 "OpenAI模型 gpt-4o-mini"）
        if not matched:
            m = re.match(r'^(.+?)[\s]*模型\s+(\S+)', line)
            if m:
                provider_text = m.group(1).strip()
                model_id = _clean_value(m.group(2))
                if "name" not in kv:
                    kv["name"] = provider_text
                if "model_id" not in kv:
                    kv["model_id"] = model_id

    return kv


def _split_into_blocks(text: str) -> list[str]:
    """将文本拆分为多个模型块"""
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 第一步：按明显分隔符切分
    separator_pattern = r'\n\s*(?:---+|===+|###+|\*\*\*+)\s*\n'
    parts = re.split(separator_pattern, text)

    all_blocks = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # 每个 part 再按双换行切分
        sub_blocks = re.split(r'\n\s*\n', part)
        for sb in sub_blocks:
            sb = sb.strip()
            if sb:
                all_blocks.append(sb)

    # 第二步：如果只有一块，尝试按编号行切分
    if len(all_blocks) <= 1:
        source = all_blocks[0] if all_blocks else text.strip()
        numbered_blocks = _split_by_numbered_lines(source)
        if len(numbered_blocks) > 1:
            all_blocks = numbered_blocks

    # 第二步半：对每个块，再尝试按中文编号切分
    expanded = []
    for block in all_blocks:
        cn_blocks = _split_by_chinese_number(block)
        if len(cn_blocks) > 1:
            expanded.extend(cn_blocks)
        else:
            expanded.append(block)
    all_blocks = expanded

    # 第三步：如果仍然只有一块，尝试按"关键词行"切分
    if len(all_blocks) <= 1:
        source = all_blocks[0] if all_blocks else text.strip()
        keyword_blocks = _split_by_keyword_lines(source)
        if len(keyword_blocks) > 1:
            all_blocks = keyword_blocks

    # 第四步：对每个块，检测是否有多个 key，拆分为子块
    expanded = []
    for block in all_blocks:
        sub_blocks = _split_by_multi_keys(block)
        expanded.extend(sub_blocks)
    all_blocks = expanded

    # 过滤注释块
    result = []
    for block in all_blocks:
        if block.startswith('#') and '\n' not in block:
            continue
        lines = block.split('\n')
        content_lines = [l for l in lines if not l.strip().startswith('#')]
        cleaned = '\n'.join(content_lines).strip()
        if cleaned:
            result.append(cleaned)

    return result if result else []


def _split_by_numbered_lines(text: str) -> list[str]:
    """按编号行切分（1. xxx / 2. xxx）"""
    pattern = r'\n(?=\s*\d+[\.\)、]\s+)'
    parts = re.split(pattern, text)
    if len(parts) > 1:
        return [p.strip() for p in parts if p.strip()]
    return []


def _split_by_chinese_number(text: str) -> list[str]:
    """按中文数字编号切分（二、xxx / 三、xxx）"""
    pattern = r'\n(?=\s*[一二三四五六七八九十]+[、．.]\s*)'
    parts = re.split(pattern, text)
    if len(parts) > 1:
        return [p.strip() for p in parts if p.strip()]
    return []


def _split_by_keyword_lines(text: str) -> list[str]:
    """
    按"关键词行"切分 — 每个模型块通常以提供商/模型相关关键词开头

    匹配模式：一行中同时包含 provider 关键词 和 model/key/url 中的至少一个
    """
    # 提供商/模型开头的行
    provider_pattern = (
        r'(?:OpenAI|DeepSeek|智谱|GLM|Moonshot|Kimi|通义|千问|Qwen|'
        r'豆包|Doubao|火山|文心|ERNIE|星火|Spark|讯飞|混元|Hunyuan|腾讯|'
        r'MiniMax|百川|Baichuan|MiMo|小米|Ollama|Anthropic|Claude|Gemini|'
        r'OpenRouter|SiliconFlow|Cloudflare|阿里|百度|字节|科大讯飞)'
    )

    lines = text.split('\n')
    split_points = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # 跳过纯注释行
        if stripped.startswith('#'):
            continue
        # 检查是否像一个模型配置的开头
        # 条件：包含提供商关键词 且 是较短的行（标题/标签行）
        if re.search(provider_pattern, stripped, re.IGNORECASE) and len(stripped) < 80:
            # 排除明显的值行（以 Key/接口/URL 等开头）
            if not re.match(r'^(?:Key|key|API|接口|地址|URL|url|状态|可用|密钥|token)', stripped, re.IGNORECASE):
                split_points.append(i)

    if len(split_points) <= 1:
        return []

    blocks = []
    for j in range(len(split_points)):
        start = split_points[j]
        end = split_points[j + 1] if j + 1 < len(split_points) else len(lines)
        block = '\n'.join(lines[start:end]).strip()
        if block:
            blocks.append(block)

    return blocks


def _split_by_multi_keys(text: str) -> list[str]:
    """
    检测块内是否有多个 API Key，如有则按 Key 行拆分为子块

    例如：
    密钥①
    接口：https://api.xiaomimimo.com/v1
    Key：sk-aaa...

    密钥②
    接口：https://api.xiaomimimo.com/v1
    Key：sk-bbb...
    """
    key_line_pattern = re.compile(
        r'(?i)^\s*(?:密钥[①②③④⑤]?(?:\（.*?\）)?|'
        r'(?:API\s*)?[Kk]ey[：:=\s]|'
        r'密钥串[：:=\s]|'
        r'token[：:=\s]|'
        r'secret[：:=\s]|'
        r'备用标识[：:=\s])',
    )

    lines = text.split('\n')
    key_line_indices = []

    for i, line in enumerate(lines):
        if key_line_pattern.match(line.strip()):
            # 确认这一行确实包含一个 key 值
            if _extract_keys(line):
                key_line_indices.append(i)

    if len(key_line_indices) <= 1:
        return [text]

    # 按 key 行拆分，每个子块从 key 行的上一行开始（保留标签行如"密钥①"）
    blocks = []
    for j in range(len(key_line_indices)):
        start = max(0, key_line_indices[j] - 1)  # 往上取一行（标签行）
        end = key_line_indices[j + 1] - 1 if j + 1 < len(key_line_indices) else len(lines)
        block = '\n'.join(lines[start:end]).strip()
        if block:
            blocks.append(block)

    return blocks


def _parse_single_block(text: str) -> ParsedModel:
    """解析单个文本块"""
    result = ParsedModel()

    # 1. JSON 尝试
    json_results = _try_parse_json(text)
    if json_results:
        data = json_results[0]
        field_mapping = {
            "name": "name", "名称": "name", "label": "name",
            "api_key": "api_key", "apiKey": "api_key", "key": "api_key",
            "api-key": "api_key", "token": "api_key", "secret": "api_key",
            "bearer_token": "api_key",
            "base_url": "base_url", "baseUrl": "base_url", "url": "base_url",
            "base-url": "base_url", "endpoint": "base_url", "baseURL": "base_url",
            "model_id": "model_id", "modelId": "model_id", "model": "model_id",
            "model-id": "model_id", "model_name": "model_id",
            "api_type": "api_type", "apiType": "api_type", "type": "api_type",
            "context_window": "context_window", "contextWindow": "context_window",
            "max_tokens": "max_tokens", "maxTokens": "max_tokens",
            "supports_vision": "supports_vision", "vision": "supports_vision",
            "supports_audio": "supports_audio", "audio": "supports_audio",
        }
        for src, dst in field_mapping.items():
            if src in data and data[src] is not None:
                if dst in ("context_window", "max_tokens"):
                    try:
                        setattr(result, dst, int(data[src]))
                    except (ValueError, TypeError):
                        pass
                elif dst in ("supports_vision", "supports_audio"):
                    setattr(result, dst, bool(data[src]))
                else:
                    setattr(result, dst, str(data[src]))

        if result.base_url or result.api_key or result.model_id:
            return _finalize_model(result, text)

    # 2. 键值对 + 正则提取
    kv = _extract_kv_pairs(text)
    urls = _extract_urls(text)
    keys = _extract_keys(text)
    model_ids = _extract_model_ids(text)

    # 填充 base_url
    if kv.get("base_url") and _is_url(kv["base_url"]):
        result.base_url = kv["base_url"]
    elif urls:
        v1_urls = [u for u in urls if "/v1" in u or "/v3" in u or "/v4" in u]
        result.base_url = _clean_url_value(v1_urls[0] if v1_urls else urls[0])

    # 填充 api_key
    if kv.get("api_key"):
        result.api_key = kv["api_key"]
    elif keys:
        result.api_key = keys[0][0]

    # 填充 model_id
    if kv.get("model_id"):
        raw = kv["model_id"]
        if _is_url(raw):
            pass
        else:
            # 先按括号提取内部的模型名（如 "含 26 个免费模型（如 gpt-oss-20b:free）"）
            bracket_models = re.findall(r'[（(]([^）)]+)[）)]', raw)
            all_candidates = []
            for bm in bracket_models:
                parts = re.split(r'[,，、]+', bm)
                all_candidates.extend([p.strip() for p in parts if p.strip()])

            # 也按逗号分隔主文本
            main_parts = re.split(r'[,，、]+', raw)
            all_candidates.extend([p.strip() for p in main_parts if p.strip()])

            # 清理：去掉前导中文（如 "如 gpt-oss" → "gpt-oss"）
            cleaned = []
            for c in all_candidates:
                c = re.sub(r'^[\u4e00-\u9fff]+\s*', '', c).strip()
                if c:
                    cleaned.append(c)

            # 过滤
            cleaned = [m for m in cleaned if _looks_like_model_id(m)]
            if cleaned:
                result.model_id = cleaned[0]
    if not result.model_id and model_ids:
        result.model_id = model_ids[0]

    # 填充 name
    if kv.get("name"):
        result.name = kv["name"]
    if kv.get("notes"):
        result.notes = kv["notes"]

    return _finalize_model(result, text)


def _finalize_model(result: ParsedModel, text: str) -> ParsedModel:
    """最终处理：推断提供商、自动填充、检测能力"""
    # 提供商推断（优先级：URL > 文本关键词 > 模型 ID）
    if result.base_url and _is_url(result.base_url):
        result.provider, _ = _detect_provider_from_url(result.base_url)
    if not result.provider:
        result.provider, _ = _detect_provider_from_text(text)
    if not result.provider and result.model_id:
        result.provider, _ = _detect_provider_from_model(result.model_id)

    # 自动填充 URL
    if not result.base_url or not _is_url(result.base_url):
        _, default_url = _detect_provider_from_text(text)
        if not default_url and result.model_id:
            _, default_url = _detect_provider_from_model(result.model_id)
        if default_url:
            result.base_url = default_url

    # 自动生成名称
    if not result.name:
        if result.provider:
            result.name = result.provider
            if result.model_id:
                result.name += f" - {result.model_id}"
        elif result.model_id:
            result.name = result.model_id

    # 检测能力
    text_lower = text.lower()
    for kw in VISION_KEYWORDS:
        if kw in text_lower:
            result.supports_vision = True
            break
    for kw in AUDIO_KEYWORDS:
        if kw in text_lower:
            result.supports_audio = True
            break

    return _fill_missing(result)


def _try_parse_json(text: str) -> list[dict]:
    """尝试 JSON 解析"""
    results = []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            results.extend(data)
        elif isinstance(data, dict):
            results.append(data)
        return results
    except json.JSONDecodeError:
        pass

    json_pattern = r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})'
    for match in re.finditer(json_pattern, text):
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and any(k in data for k in ["api_key", "base_url", "model", "model_id", "key"]):
                results.append(data)
        except json.JSONDecodeError:
            continue

    return results


# ============ 主入口 ============

def parse_smart_paste(text: str) -> list[ParsedModel]:
    """智能粘贴解析主入口"""
    if not text or not text.strip():
        return []

    blocks = _split_into_blocks(text)

    results = []
    for block in blocks:
        parsed = _parse_single_block(block)
        if parsed.base_url or parsed.api_key or parsed.model_id:
            results.append(parsed)

    # 去重
    seen = set()
    unique = []
    for r in results:
        key = (r.base_url, r.model_id, r.api_key)
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique if unique else []


def get_provider_suggestions(keyword: str) -> list[dict]:
    """根据关键词搜索提供商"""
    keyword = keyword.lower()
    suggestions = []
    for keywords, provider, default_url, api_type in PROVIDER_DB:
        for kw in keywords:
            if keyword in kw or kw in keyword:
                suggestions.append({
                    "provider": provider,
                    "base_url": default_url,
                    "api_type": api_type,
                    "keywords": keywords,
                })
                break
    return suggestions
