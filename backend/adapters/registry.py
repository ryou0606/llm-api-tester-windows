"""
适配器注册表 - 管理所有可用的 API 适配器

根据模型配置中的 api_type 字段，自动选择对应的适配器实例。
"""

from adapters.base import BaseModelAdapter
from adapters.openai_compat import OpenAICompatAdapter


class AdapterRegistry:
    """
    适配器注册表

    维护 api_type -> adapter 实例 的映射。
    添加新的 API 格式支持时，只需：
    1. 创建新的适配器子类
    2. 在 _adapters 字典中注册
    """

    def __init__(self):
        self._adapters: dict[str, BaseModelAdapter] = {}
        self._register_defaults()

    def _register_defaults(self):
        """注册默认适配器"""
        openai_adapter = OpenAICompatAdapter()

        # OpenAI 兼容格式覆盖大部分厂商
        self._adapters["openai_compat"] = openai_adapter

        # 以下厂商也使用 OpenAI 兼容格式，注册同一个适配器实例
        # （未来如果有差异，可以替换为独立实现）
        self._adapters["openai"] = openai_adapter
        self._adapters["deepseek"] = openai_adapter
        self._adapters["moonshot"] = openai_adapter
        self._adapters["zhipu"] = openai_adapter
        self._adapters["baichuan"] = openai_adapter
        self._adapters["minimax"] = openai_adapter
        self._adapters["01ai"] = openai_adapter
        self._adapters["stepfun"] = openai_adapter
        self._adapters["siliconflow"] = openai_adapter
        self._adapters["together"] = openai_adapter
        self._adapters["groq"] = openai_adapter
        self._adapters["fireworks"] = openai_adapter
        self._adapters["openrouter"] = openai_adapter
        self._adapters["xiaomi"] = openai_adapter

        # TODO: 后续阶段实现以下适配器
        # self._adapters["anthropic"] = AnthropicAdapter()
        # self._adapters["gemini"] = GeminiAdapter()
        # self._adapters["wenxin"] = WenxinAdapter()
        # self._adapters["tongyi"] = TongyiAdapter()

    def get(self, api_type: str) -> BaseModelAdapter:
        """
        获取指定 API 类型的适配器

        Args:
            api_type: API 格式类型

        Returns:
            对应的适配器实例

        Raises:
            ValueError: 不支持的 API 类型
        """
        adapter = self._adapters.get(api_type)
        if adapter is None:
            supported = ", ".join(sorted(self._adapters.keys()))
            raise ValueError(
                f"不支持的 API 类型: '{api_type}'。支持的类型: {supported}"
            )
        return adapter

    def register(self, api_type: str, adapter: BaseModelAdapter):
        """注册新的适配器"""
        self._adapters[api_type] = adapter

    @property
    def supported_types(self) -> list[str]:
        """返回所有支持的 API 类型"""
        return sorted(set(self._adapters.keys()))


# 全局单例
adapter_registry = AdapterRegistry()
