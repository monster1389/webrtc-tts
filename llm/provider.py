"""
LLM 提供者接口定义
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional


class LLMProvider(ABC):
    """LLM 提供者抽象基类"""
    
    @abstractmethod
    async def generate_response_stream(self, text: str) -> AsyncGenerator[str, None]:
        """
        流式生成回复文本
        
        Args:
            text: 输入文本
            
        Yields:
            回复文本的片段
        """
        pass
    
    @abstractmethod
    async def generate_response(self, text: str) -> str:
        """
        非流式生成回复文本
        
        Args:
            text: 输入文本
            
        Returns:
            完整的回复文本
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        获取提供者名称
        
        Returns:
            提供者名称
        """
        pass
