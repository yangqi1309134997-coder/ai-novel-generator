"""
提供商预设配置 - 20+常见LLM提供商的默认配置

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """提供商配置"""
    id: str                       # 唯一标识
    name: str                     # 显示名称
    base_url: str                 # API地址
    models: List[str]             # 支持的模型列表
    default_model: str            # 默认模型
    requires_key: bool            # 是否需要API Key
    is_local: bool = False        # 是否为本地服务
    icon: Optional[str] = None    # 图标（emoji或URL）
    description: Optional[str] = None  # 描述
    api_key_header: str = "Authorization"  # API Key请求头
    api_key_prefix: str = "Bearer "  # API Key前缀


# 20+ 预设提供商配置
PRESET_PROVIDERS: Dict[str, ProviderConfig] = {
    "OpenAI": ProviderConfig(
        id="openai",
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        default_model="gpt-4o",
        requires_key=True,
        icon="🤖",
        description="官方OpenAI API"
    ),

    "Anthropic": ProviderConfig(
        id="anthropic",
        name="Anthropic (Claude)",
        base_url="https://api.anthropic.com",
        models=["claude-sonnet-4-5-20250929", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
        default_model="claude-sonnet-4-5-20250929",
        requires_key=True,
        api_key_header="x-api-key",
        api_key_prefix="",
        icon="🧠",
        description="Claude系列模型"
    ),

    "Google": ProviderConfig(
        id="google",
        name="Google Gemini",
        base_url="https://generativelanguage.googleapis.com",
        models=["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
        default_model="gemini-2.0-flash-exp",
        requires_key=True,
        api_key_header="x-goog-api-key",
        api_key_prefix="",
        icon="🔍",
        description="Google Gemini模型"
    ),

    "OpenAI Compatible": ProviderConfig(
        id="openai_compatible",
        name="OpenAI兼容接口",
        base_url="",
        models=["gpt-3.5-turbo", "gpt-4"],
        default_model="gpt-3.5-turbo",
        requires_key=True,
        icon="🔌",
        description="兼容OpenAI API格式的第三方服务"
    ),

    "Alibaba": ProviderConfig(
        id="alibaba",
        name="阿里通义千问",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        models=["qwen-turbo", "qwen-plus", "qwen-max", "qwen-2.5-coder-32b-instruct"],
        default_model="qwen-turbo",
        requires_key=True,
        icon="☁️",
        description="阿里云通义千问系列"
    ),

    "DeepSeek": ProviderConfig(
        id="deepseek",
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        models=["deepseek-chat", "deepseek-coder"],
        default_model="deepseek-chat",
        requires_key=True,
        icon="🔥",
        description="DeepSeek-V3高性能模型"
    ),

    "Zhipu AI": ProviderConfig(
        id="zhipu",
        name="智谱AI (GLM)",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        models=["glm-4", "glm-4-plus", "glm-4-flash", "glm-4-air", "glm-4.5-air", "glm-4.5-flash", "glm-4.5-plus"],
        default_model="glm-4",
        requires_key=True,
        icon="🎯",
        description="智谱GLM系列"
    ),

    "Groq": ProviderConfig(
        id="groq",
        name="Groq",
        base_url="https://api.groq.com/openai",
        models=["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        default_model="llama-3.3-70b-versatile",
        requires_key=True,
        icon="⚡",
        description="超高速推理"
    ),

    "Ollama": ProviderConfig(
        id="ollama",
        name="Ollama (本地)",
        base_url="http://localhost:11434/v1",
        models=["llama3.2", "qwen2.5", "mistral", "deepseek-r1"],
        default_model="llama3.2",
        requires_key=False,
        is_local=True,
        icon="🦙",
        description="本地部署的开源模型"
    ),

    "LM Studio": ProviderConfig(
        id="lm_studio",
        name="LM Studio (本地)",
        base_url="http://localhost:1234/v1",
        models=["local-model"],
        default_model="local-model",
        requires_key=False,
        is_local=True,
        icon="💻",
        description="本地推理服务器"
    ),

    "Together AI": ProviderConfig(
        id="together",
        name="Together AI",
        base_url="https://api.together.xyz/v1",
        models=["meta-llama/Llama-3.3-70B-Instruct-Turbo", "mistralai/Mixtral-8x7B-Instruct-v0.1"],
        default_model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        requires_key=True,
        icon="🚀",
        description="开源模型托管平台"
    ),

    "Moonshot": ProviderConfig(
        id="moonshot",
        name="Moonshot AI (Kimi)",
        base_url="https://api.moonshot.cn/v1",
        models=["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        default_model="moonshot-v1-8k",
        requires_key=True,
        icon="🌙",
        description="Moonshot AI Kimi系列"
    ),

    "Baichuan": ProviderConfig(
        id="baichuan",
        name="百川智能",
        base_url="https://api.baichuan-ai.com/v1",
        models=["Baichuan2-Turbo", "Baichuan2-53B"],
        default_model="Baichuan2-Turbo",
        requires_key=True,
        icon="🏔️",
        description="百川大模型"
    ),

    "Minimax": ProviderConfig(
        id="minimax",
        name="MiniMax",
        base_url="https://api.minimax.chat/v1",
        models=["abab6.5s-chat", "abab6.5-chat"],
        default_model="abab6.5s-chat",
        requires_key=True,
        icon="🎨",
        description="MiniMax系列"
    ),

    "Xunfei": ProviderConfig(
        id="xunfei",
        name="讯飞星火",
        base_url="https://spark-api.xf-yun.com/v1",
        models=["spark-lite", "spark-pro", "spark-max"],
        default_model="spark-pro",
        requires_key=True,
        icon="✨",
        description="科大讯飞星火认知大模型"
    ),

    "Tencent": ProviderConfig(
        id="tencent",
        name="腾讯混元",
        base_url="https://api.hunyuan.cloud.tencent.com/v1",
        models=["hunyuan-lite", "hunyuan-standard", "hunyuan-pro"],
        default_model="hunyuan-standard",
        requires_key=True,
        icon="🎮",
        description="腾讯混元大模型"
    ),

    "Baidu": ProviderConfig(
        id="baidu",
        name="百度文心",
        base_url="https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop",
        models=["ernie-bot-4", "ernie-bot-turbo"],
        default_model="ernie-bot-4",
        requires_key=True,
        icon="🐻",
        description="百度文心一言"
    ),

    "Perplexity": ProviderConfig(
        id="perplexity",
        name="Perplexity AI",
        base_url="https://api.perplexity.ai",
        models=["llama-3.1-sonar-huge-128k-online", "llama-3.1-sonar-small-128k-online"],
        default_model="llama-3.1-sonar-huge-128k-online",
        requires_key=True,
        icon="🔮",
        description="带联网搜索的AI"
    ),

    "Mistral AI": ProviderConfig(
        id="mistral",
        name="Mistral AI",
        base_url="https://api.mistral.ai/v1",
        models=["mistral-large-latest", "mistral-medium-latest", "codestral-latest"],
        default_model="mistral-large-latest",
        requires_key=True,
        icon="🌊",
        description="Mistral开源模型"
    ),

    "Replicate": ProviderConfig(
        id="replicate",
        name="Replicate",
        base_url="https://api.replicate.com/v1",
        models=["meta-llama-3.1-70b", "mistralai/mixtral-8x7b-instruct-v0.1"],
        default_model="meta-llama-3.1-70b",
        requires_key=True,
        icon="🔁",
        description="开源模型托管"
    ),

    "Novita AI": ProviderConfig(
        id="novita",
        name="Novita AI",
        base_url="https://api.novita.ai/v3",
        models=["gemma-2-27b-it", "llama-3.1-70b-instruct"],
        default_model="llama-3.1-70b-instruct",
        requires_key=True,
        icon="💎",
        description="高性能推理"
    ),

    "SiliconFlow": ProviderConfig(
        id="siliconflow",
        name="硅基流动",
        base_url="https://api.siliconflow.cn/v1",
        models=["Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3"],
        default_model="Qwen/Qwen2.5-72B-Instruct",
        requires_key=True,
        icon="⚙️",
        description="国产大模型平台"
    ),
}


class ProviderFactory:
    """提供商工厂"""

    @staticmethod
    def get_provider_config(provider_id: str) -> Optional[ProviderConfig]:
        """
        获取提供商配置

        Args:
            provider_id: 提供商ID

        Returns:
            ProviderConfig对象，如果不存在则返回None
        """
        logger.debug(f"[提供商] 查找提供商配置: {provider_id}")

        # 直接查找
        config = PRESET_PROVIDERS.get(provider_id)
        if config:
            logger.debug(f"[提供商] 找到提供商: {config.name}")
            return config

        # 尝试模糊匹配（处理大小写、空格等问题）
        provider_id_lower = provider_id.lower().replace(" ", "").replace("_", "").replace("-", "")

        # 构建ID映射表
        id_mapping = {
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "google": "Google",
            "alibaba": "Alibaba",
            "deepseek": "DeepSeek",
            "zhipu": "Zhipu AI",
            "baichuan": "Baichuan",
            "baidu": "Baidu",
            "tencent": "Tencent",
            "xunfei": "Xunfei",
            "moonshot": "Moonshot",
            "minimax": "Minimax",
            "mistral": "Mistral AI",
            "groq": "Groq",
            "together": "Together AI",
            "perplexity": "Perplexity",
            "replicate": "Replicate",
            "novita": "Novita AI",
            "siliconflow": "SiliconFlow",
            "ollama": "Ollama",
            "lmstudio": "LM Studio",
            "openaicompatible": "OpenAI Compatible"
        }

        mapped_name = id_mapping.get(provider_id_lower)
        if mapped_name:
            return PRESET_PROVIDERS.get(mapped_name)

        # 如果还是找不到，打印警告
        logger.warning(f"[提供商] 未找到提供商配置: {provider_id} (尝试了模糊匹配)")
        return None

    @staticmethod
    def list_providers() -> List[str]:
        """获取所有提供商ID列表"""
        return list(PRESET_PROVIDERS.keys())

    @staticmethod
    def list_providers_with_info() -> List[Dict[str, Any]]:
        """
        获取所有提供商的详细信息

        Returns:
            包含提供商信息的字典列表
        """
        return [
            {
                "id": config.id,
                "name": config.name,
                "icon": config.icon,
                "description": config.description,
                "is_local": config.is_local,
                "requires_key": config.requires_key
            }
            for config in PRESET_PROVIDERS.values()
        ]

    @staticmethod
    def get_provider_by_name(name: str) -> Optional[ProviderConfig]:
        """
        根据显示名称查找提供商

        Args:
            name: 显示名称

        Returns:
            ProviderConfig对象
        """
        for config in PRESET_PROVIDERS.values():
            if config.name == name:
                return config
        return None

    @staticmethod
    def add_custom_provider(
        provider_id: str,
        name: str,
        base_url: str,
        models: List[str],
        default_model: str,
        requires_key: bool = True,
        **kwargs
    ) -> None:
        """
        添加自定义提供商

        Args:
            provider_id: 唯一ID
            name: 显示名称
            base_url: API地址
            models: 支持的模型
            default_model: 默认模型
            requires_key: 是否需要API Key
            **kwargs: 其他参数
        """
        PRESET_PROVIDERS[provider_id] = ProviderConfig(
            id=provider_id,
            name=name,
            base_url=base_url,
            models=models,
            default_model=default_model,
            requires_key=requires_key,
            **kwargs
        )

        logger.info(f"[提供商] 添加自定义提供商: {name} ({provider_id}), base_url={base_url}")

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        验证URL格式

        Args:
            url: URL字符串

        Returns:
            是否有效
        """
        if not url:
            return True  # 空URL是有效的（用户会稍后填写）

        # 基本的URL格式检查
        if not (url.startswith("http://") or url.startswith("https://")):
            return False

        # 检查是否有协议后的内容
        if len(url) <= 8:
            return False

        return True

    @staticmethod
    def sanitize_url(url: str) -> str:
        """
        清理URL，移除不安全的部分

        Args:
            url: 原始URL

        Returns:
            清理后的URL
        """
        # 移除首尾空格
        url = url.strip()

        # 确保有协议
        if not url.startswith(("http://", "https://")):
            if url.startswith("localhost"):
                url = "http://" + url
            else:
                url = "https://" + url

        return url


def get_provider_for_quickstart() -> ProviderConfig:
    """
    获取推荐用于快速开始的提供商

    Returns:
        推荐的提供商配置
    """
    # 按优先级：Ollama（本地免费） > OpenAI（稳定） > 其他
    if PRESET_PROVIDERS.get("ollama"):
        return PRESET_PROVIDERS["ollama"]
    if PRESET_PROVIDERS.get("openai"):
        return PRESET_PROVIDERS["openai"]

    # 如果没有上述提供商，返回第一个
    return next(iter(PRESET_PROVIDERS.values()))
