"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    environment: str = "dev"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql://ragchatbot:ragchatbot@localhost:5432/ragchatbot"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Vector DB
    vector_db_host: str = "localhost"
    vector_db_port: int = 8001
    vector_db_collection: str = "knowledge_base"

    # LLM (Groq, OpenAI-compatible API)
    groq_api_key: str = ""
    groq_llm_model: str = "openai/gpt-oss-120b"

    # OpenAI (kept for optional use)
    openai_api_key: str = ""
    openai_llm_model: str = "gpt-4o"

    # Embedding model (HuggingFace sentence-transformers, runs locally)
    hf_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Storage
    storage_type: str = "local"
    storage_path: str = "./data/documents"

    # RAG Config
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 5
    similarity_threshold: float = 0.7
    max_context_tokens: int = 8000

    # Rate Limiting
    rate_limit_rpm: int = 60

    # CORS
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
