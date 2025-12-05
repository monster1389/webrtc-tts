"""
本地 LLM 提供者实现（示例）
"""
import asyncio
from typing import AsyncGenerator, Dict, Any
from ..llm.provider import LLMProvider


class LocalProvider(LLMProvider):
    """本地提供者（示例实现）"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化本地提供者
        
        Args:
            config: 提供者配置
        """
        self.config = config
        self.model = config.get("model", "local-model")
    
    async def generate_response_stream(self, text: str) -> AsyncGenerator[str, None]:
        """
        流式生成回复文本（示例实现）
        
        Args:
            text: 输入文本
            
        Yields:
            回复文本的片段
        """
        # 示例：模拟流式响应
        response = f"这是本地模型对 '{text}' 的回复。这是一个示例回复，实际使用时需要连接本地模型服务。"
        
        # 模拟流式输出
        words = response.split()
        for word in words:
            await asyncio.sleep(0.1)  # 模拟延迟
            yield word + " "
    
    async def generate_response(self, text: str) -> str:
        """
        非流式生成回复文本（示例实现）
        
        Args:
            text: 输入文本
            
        Returns:
            完整的回复文本
        """
        # 示例：模拟响应
        return f"这是本地模型对 '{text}' 的回复。这是一个示例回复，实际使用时需要连接本地模型服务。"
    
    def get_name(self) -> str:
        """
        获取提供者名称
        
        Returns:
            提供者名称
        """
        return "Local"
