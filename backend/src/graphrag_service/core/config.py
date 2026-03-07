"""
Application configuration using Pydantic settings.
"""

from functools import lru_cache
from typing import List

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = Field(default="GraphRAG Service", description="Application name")
    APP_DESCRIPTION: str = Field(
        default="Graph RAG over Papers With Code data using Neo4j",
        description="Application description",
    )
    APP_HOST: str = Field(default="0.0.0.0", description="Server host")
    APP_PORT: int = Field(default=8005, description="Server port")
    APP_ENVIRONMENT: str = Field(
        default="development", description="Application environment"
    )
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    APP_DEBUG: bool = Field(default=False, description="Application debug")

    APP_X_API_KEY: str = Field(
        default="changeme",
        description="API key for X-API-Key header authentication",
    )

    ALLOWED_ORIGINS_STR: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="CORS allowed origins (comma-separated)",
    )

    @property
    def allowed_origins(self) -> List[str]:
        """Parse allowed_origins from comma-separated string."""
        if not self.ALLOWED_ORIGINS_STR:
            return ["*"]
        if "," in self.ALLOWED_ORIGINS_STR:
            return [origin.strip() for origin in self.ALLOWED_ORIGINS_STR.split(",")]
        return [self.ALLOWED_ORIGINS_STR.strip()]

    # Neo4j Settings
    NEO4J_URI: str = Field(default="bolt://localhost:7687", description="Neo4j bolt URI")
    NEO4J_USER: str = Field(default="neo4j", description="Neo4j username")
    NEO4J_PASSWORD: str = Field(default="password123", description="Neo4j password")

    # LLM (provider-agnostic via LangChain)
    LLM_PROVIDER: str = Field(default="openai", description="LLM provider (openai|google|ollama|qwen)")
    LLM_MODEL: str = Field(default="gpt-4o-mini", description="LLM model name")

    # Embeddings (provider-agnostic via LangChain)
    EMBEDDING_PROVIDER: str = Field(default="openai", description="Embedding provider (openai|google|ollama|qwen)")
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", description="Embedding model name")
    EMBEDDING_DIM: int = Field(default=1536, description="Embedding dimension")

    # Provider API Keys
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key")
    GOOGLE_API_KEY: str = Field(default="", description="Google API key")
    QWEN_API_KEY: str = Field(default="", description="Qwen / DashScope API key")
    QWEN_BASE_URL: str = Field(default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1", description="Qwen / DashScope base URL")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Ollama base URL")

    # RAG Settings
    TOP_K_SEED_NODES: int = Field(
        default=5, description="Number of seed nodes for vector search"
    )
    TRAVERSAL_DEPTH: int = Field(default=2, description="Graph traversal depth")

    # Data Settings
    DATA_DIR: str = Field(default="data", description="Data directory path")
    MAX_PAPERS: int = Field(default=5000, description="Max papers to ingest (0 = all)")
    MAX_METHODS: int = Field(default=0, description="Max methods to ingest (0 = all)")
    MAX_TASKS: int = Field(default=0, description="Max tasks to ingest (0 = all)")
    MAX_DATASETS: int = Field(default=0, description="Max datasets to ingest (0 = all)")
    INGEST_BATCH_SIZE: int = Field(default=50, description="Ingestion batch size")

    # Environment alias
    @property
    def ENVIRONMENT(self) -> str:
        """Alias for APP_ENVIRONMENT."""
        return self.APP_ENVIRONMENT


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
