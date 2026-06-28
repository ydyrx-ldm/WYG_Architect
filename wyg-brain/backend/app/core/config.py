"""WYG Brain - 外脑 App 后端配置"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional
from enum import Enum

# .env 文件路径：始终从 backend 目录查找
BACKEND_DIR = Path(__file__).parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class LLMProvider(str, Enum):
    DEEPSEEK = "deepseek"
    DOUBAO = "doubao"
    OLLAMA = "ollama"


class Settings(BaseSettings):
    # App
    APP_NAME: str = "WYG Brain"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./wyg_brain.db"

    # LLM - DeepSeek (主力)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # LLM - 豆包 (备用)
    DOUBAO_API_KEY: str = ""
    DOUBAO_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    DOUBAO_MODEL: str = "doubao-pro-32k"

    # LLM - Ollama (未来)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # Default provider
    DEFAULT_LLM_PROVIDER: LLMProvider = LLMProvider.DEEPSEEK

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30

    # Storage
    MEDIA_DIR: str = "./media"

    model_config = {"env_file": str(ENV_FILE), "env_file_encoding": "utf-8"}


settings = Settings()
