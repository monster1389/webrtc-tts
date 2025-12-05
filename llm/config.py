"""
LLM 配置管理
"""
import json
import os
from typing import Dict, Any


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径，如果为 None 则使用默认路径
        
    Returns:
        配置字典
    """
    if config_path is None:
        # 默认配置文件路径
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    
    if not os.path.exists(config_path):
        # 如果配置文件不存在，使用环境变量
        return load_config_from_env()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return load_config_from_env()


def load_config_from_env() -> Dict[str, Any]:
    """
    从环境变量加载配置
    
    Returns:
        配置字典
    """
    config = {
        "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
        "providers": {
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
                "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "1000")),
            },
            "dashscope": {
                "api_key": os.getenv("DASHSCOPE_API_KEY", ""),
                "base_url": os.getenv("DASHSCOPE_BASE_URL", 
                                     "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                "model": os.getenv("DASHSCOPE_MODEL", "qwen-plus"),
                "temperature": float(os.getenv("DASHSCOPE_TEMPERATURE", "0.7")),
                "max_tokens": int(os.getenv("DASHSCOPE_MAX_TOKENS", "1000")),
            }
        }
    }
    return config


def get_provider_config(config: Dict[str, Any], provider_name: str = None) -> Dict[str, Any]:
    """
    获取指定提供者的配置
    
    Args:
        config: 完整配置字典
        provider_name: 提供者名称，如果为 None 则使用配置中的 llm_provider
        
    Returns:
        提供者配置字典
    """
    if provider_name is None:
        provider_name = config.get("llm_provider", "openai")
    
    providers = config.get("providers", {})
    if provider_name not in providers:
        raise ValueError(f"未找到提供者配置: {provider_name}")
    
    return providers[provider_name]
