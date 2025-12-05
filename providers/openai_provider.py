"""
OpenAI LLM 提供者实现
"""
import os
from typing import AsyncGenerator, Dict, Any
from openai import AsyncOpenAI
from llm.provider import LLMProvider

PROMPT = """你是一只笨蛋猫娘"""

class OpenAIProvider(LLMProvider):
    """OpenAI 提供者"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 OpenAI 提供者
        
        Args:
            config: 提供者配置
        """
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", "https://api.openai.com/v1"),
        )
        self.model = config.get("model", "gpt-3.5-turbo")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 1000)
    
    async def generate_response_stream(self, text: str) -> AsyncGenerator[str, None]:
        """
        流式生成回复文本
        
        Args:
            text: 输入文本
            
        Yields:
            回复文本的片段
        """
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": text}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
        
        except Exception as e:
            yield f"OpenAI API 错误: {str(e)}"
    
    async def generate_response(self, text: str) -> str:
        """
        非流式生成回复文本
        
        Args:
            text: 输入文本
            
        Returns:
            完整的回复文本
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": text}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            return response.choices[0].message.content or ""
        
        except Exception as e:
            return f"OpenAI API 错误: {str(e)}"
    
    def get_name(self) -> str:
        """
        获取提供者名称
        
        Returns:
            提供者名称
        """
        return "OpenAI"
