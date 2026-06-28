"""LLM 抽象层 - 统一接口，支持 DeepSeek / 豆包 / Ollama 切换

使用 httpx 直接调用 OpenAI 兼容 API，避免 SDK 对非标准字段（如 reasoning_content）的解析问题。
"""

import httpx
import json
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from app.core.config import settings, LLMProvider


class LLMProviderBase(ABC):
    """LLM 提供者基类"""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> str:
        """同步对话，返回完整回复"""
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> AsyncGenerator[str, None]:
        """流式对话，逐 token 返回"""
        ...


class OpenAICompatProvider(LLMProviderBase):
    """OpenAI 兼容 API 提供者（使用 httpx 直接调用）

    支持 DeepSeek、豆包、Ollama、GLM-5 等所有 OpenAI 兼容 API。
    直接解析 JSON 响应，避免 SDK 对非标准字段（如 reasoning_content）的解析问题。
    """

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _extract_content(self, message: dict) -> str:
        """提取回复内容，兼容推理模型（reasoning_content）"""
        content = message.get("content") or ""
        reasoning = message.get("reasoning_content") or ""
        if not content and reasoning:
            return reasoning
        if content and reasoning:
            return f"{content}\n\n---\n💡 推理过程:\n{reasoning}"
        return content

    async def chat(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 8192) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            r.raise_for_status()
            data = r.json()

        if not data.get("choices"):
            raise ValueError(f"LLM 返回空响应: {json.dumps(data, ensure_ascii=False)[:500]}")

        message = data["choices"][0].get("message", {})
        return self._extract_content(message)

    async def chat_stream(self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 8192) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if delta.get("content"):
                            yield delta["content"]
                        if delta.get("reasoning_content"):
                            yield delta["reasoning_content"]
                    except json.JSONDecodeError:
                        continue


# 提供者工厂函数
def _create_deepseek() -> OpenAICompatProvider:
    return OpenAICompatProvider(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        model=settings.DEEPSEEK_MODEL,
    )

def _create_doubao() -> OpenAICompatProvider:
    return OpenAICompatProvider(
        api_key=settings.DOUBAO_API_KEY,
        base_url=settings.DOUBAO_BASE_URL,
        model=settings.DOUBAO_MODEL,
    )

def _create_ollama() -> OpenAICompatProvider:
    return OpenAICompatProvider(
        api_key="ollama",
        base_url=f"{settings.OLLAMA_BASE_URL}/v1",
        model=settings.OLLAMA_MODEL,
    )


# 提供者注册表
_PROVIDERS = {
    LLMProvider.DEEPSEEK: _create_deepseek,
    LLMProvider.DOUBAO: _create_doubao,
    LLMProvider.OLLAMA: _create_ollama,
}

# 单例缓存
_instances: dict[LLMProvider, OpenAICompatProvider] = {}


def get_llm(provider: Optional[LLMProvider] = None) -> OpenAICompatProvider:
    """获取 LLM 提供者实例（单例）"""
    provider = provider or settings.DEFAULT_LLM_PROVIDER
    if provider not in _instances:
        factory = _PROVIDERS.get(provider)
        if not factory:
            raise ValueError(f"Unknown LLM provider: {provider}")
        _instances[provider] = factory()
    return _instances[provider]
