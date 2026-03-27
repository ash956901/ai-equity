"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

ROOT_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

load_dotenv(ROOT_ENV_FILE, override=False)


class Settings(BaseSettings):
    """Application settings from environment."""

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    debug: bool = False

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/equity_research"

    # Redis (optional)
    redis_url: Optional[str] = None

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None

    # LLM
    llm_provider: Literal["ollama", "deepseek", "openai", "groq"] = "ollama"
    # Optional global override model from .env (takes priority if set)
    llm_model: Optional[str] = None
    # Optional documented list for UI/ops discoverability, comma-separated in .env
    llm_model_options: Optional[str] = None
    llm_temperature: float = 0.3

    # Provider-specific default chat models
    ollama_model: str = "deepseek-r1:8b"
    deepseek_model: str = "deepseek-chat"
    openai_model: str = "gpt-4o-mini"
    groq_model: str = "moonshotai/kimi-k2-instruct"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # DeepSeek API (when llm_provider=deepseek)
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: str = "https://api.deepseek.com"

    # OpenAI (when llm_provider=openai)
    openai_api_key: Optional[str] = None

    # Groq API (when llm_provider=groq)
    groq_api_key: Optional[str] = None
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Embeddings (Ollama local / OpenAI)
    embedding_provider: str = "ollama"  # ollama | openai
    embedding_model: str = "nomic-embed-text"  # For Ollama
    embedding_dim: int = 768  # nomic=768, openai-3-small=1536

    # S3 / Object storage (optional)
    s3_bucket: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "ap-south-1"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: Optional[str] = None

    # Deep multi-agent orchestration
    workflow_runs_dir: str = "workflow_runs"
    deep_agent_max_steps: int = 6

    # Optional web search augmentation
    tavily_api_key: Optional[str] = None

    # External data API keys
    fmp_api_key: Optional[str] = None
    fred_api_key: Optional[str] = None
    news_api_key: Optional[str] = None
    newsdata_api_key: Optional[str] = None

    # Upstox
    upstox_api_key: Optional[str] = None
    upstox_api_secret: Optional[str] = None
    upstox_access_token: Optional[str] = None

    # Kite Connect (Zerodha)
    kite_api_key: Optional[str] = None
    kite_api_secret: Optional[str] = None
    kite_access_token: Optional[str] = None

    class Config:
        env_file = str(ROOT_ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"

    def get_llm_model(self, override_model: Optional[str] = None) -> str:
        """Resolve active model name from explicit override, generic env var, or provider default."""
        if override_model:
            return override_model
        if self.llm_model:
            return self.llm_model
        if self.llm_provider == "ollama":
            return self.ollama_model
        if self.llm_provider == "deepseek":
            return self.deepseek_model
        if self.llm_provider == "openai":
            return self.openai_model
        if self.llm_provider == "groq":
            return self.groq_model
        return self.ollama_model


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
