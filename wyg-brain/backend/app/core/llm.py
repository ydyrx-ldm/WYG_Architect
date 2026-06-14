"""LLM 抽象层 - 统一接口，支持 DeepSeek / 豆包 / Ollama 切换"""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI
from app.core.config import settings, LLMProvider


class LLMProviderBase(ABC):
    """LLM 提供者基类"""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """同步对话，返回完整回复"""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """流式对话，逐 token 返回"""
        ...


class DeepSeekProvider(LLMProviderBase):
    """DeepSeek API 提供者（兼容 OpenAI SDK）"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        self.model = settings.DEEPSEEK_MODEL

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def chat_stream(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class DoubaoProvider(LLMProviderBase):
    """豆包（火山方舟）API 提供者（兼容 OpenAI SDK）"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DOUBAO_API_KEY,
            base_url=settings.DOUBAO_BASE_URL,
        )
        self.model = settings.DOUBAO_MODEL

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def chat_stream(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class OllamaProvider(LLMProviderBase):
    """Ollama 本地模型提供者（兼容 OpenAI SDK）"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key="ollama",
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
        )
        self.model = settings.OLLAMA_MODEL

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def chat_stream(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 4096) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# 提供者注册表
_PROVIDERS: dict[LLMProvider, type[LLMProviderBase]] = {
    LLMProvider.DEEPSEEK: DeepSeekProvider,
    LLMProvider.DOUBAO: DoubaoProvider,
    LLMProvider.OLLAMA: OllamaProvider,
}

# 单例缓存
_instances: dict[LLMProvider, LLMProviderBase] = {}


def get_llm(provider: Optional[LLMProvider] = None) -> LLMProviderBase:
    """获取 LLM 提供者实例（单例）"""
    provider = provider or settings.DEFAULT_LLM_PROVIDER
    if provider not in _instances:
        cls = _PROVIDERS.get(provider)
        if not cls:
            raise ValueError(f"Unknown LLM provider: {provider}")
        _instances[provider] = cls()
    return _instances[provider]
