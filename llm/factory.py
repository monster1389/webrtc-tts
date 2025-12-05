"""
LLM 提供者工厂
"""
from typing import Dict, Any
from .provider import LLMProvider
from .config import get_provider_config


def create_llm_provider(config: Dict[str, Any], provider_name: str = None) -> LLMProvider:
    """
    创建 LLM 提供者实例
    
    Args:
        config: 配置字典
        provider_name: 提供者名称，如果为 None 则使用配置中的 llm_provider
        
    Returns:
        LLMProvider 实例
    """
    if provider_name is None:
        provider_name = config.get("llm_provider", "openai")
    
    provider_config = get_provider_config(config, provider_name)
    
    if provider_name == "openai":
        from providers.openai_provider import OpenAIProvider
        return OpenAIProvider(provider_config)
    elif provider_name == "dashscope":
        from providers.dashscope_provider import DashScopeProvider
        return DashScopeProvider(provider_config)
    elif provider_name == "local":
        from providers.local_provider import LocalProvider
        return LocalProvider(provider_config)
    else:
        raise ValueError(f"不支持的 LLM 提供者: {provider_name}")
