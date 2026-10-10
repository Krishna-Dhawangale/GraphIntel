from typing import List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "GraphIntel Market Intelligence"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "graphintel-super-secure-change-this-in-production-jwt-secret-key-32chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # CORS & Trusted Hosts
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ]
    ALLOWED_HOSTS: List[str] = ["*"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        import json

        return json.loads(v)

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        import json

        return json.loads(v)

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "graphintel"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    DATABASE_URL: str = "sqlite:///./graphintel.db"
    ASYNC_DATABASE_URL: str = "sqlite+aiosqlite:///./graphintel.db"

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None
    RATE_LIMIT_ENABLED: bool = True

    # MinIO / Object Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "graphintel-documents"
    MINIO_USE_SSL: bool = False
    STORAGE_PROVIDER: str = "local"  # "minio" or "local"
    STORAGE_LOCAL_DIR: str = "./storage_data"

    # Qdrant Vector Store
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "graphintel_chunks"
    QDRANT_API_KEY: str = ""
    VECTOR_STORE_PROVIDER: str = "memory"  # "qdrant" or "memory"

    # Embedding Configuration
    EMBEDDING_PROVIDER: str = "local"  # "openai", "gemini", or "local"
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIMENSION: int = 384

    # LLM Configuration
    LLM_PROVIDER: str = "mock"  # "openai", "gemini", "ollama", or "mock"
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:8b"

    # Document Chunking & Ingestion Limits
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_REQUEST_BODY_SIZE_MB: int = 55

    # Neo4j Knowledge Graph Configuration
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "graphintel123"
    NEO4J_DATABASE: str = "neo4j"
    GRAPH_STORE_PROVIDER: str = "neo4j"  # "neo4j" or "memory"
    MAX_GRAPH_HOPS: int = 3

    # Reranker Configuration
    RERANKER_PROVIDER: str = "cohere"  # "cohere", "simple", "bge", "none"
    COHERE_API_KEY: str = ""
    COHERE_RERANK_MODEL: str = "rerank-v3.5"

    # RAG Settings
    TOP_K: int = 5

    # Email / SMTP Configuration (for password reset)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_TLS: bool = True
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "noreply@graphintel.ai"
    EMAILS_FROM_NAME: str = "GraphIntel"
    FRONTEND_URL: str = "http://localhost:3000"
    EMAIL_ENABLED: bool = False  # Set True when SMTP credentials are configured

    # Resilience Timeouts
    LLM_TIMEOUT_SECONDS: float = 30.0
    NEO4J_TIMEOUT_SECONDS: float = 15.0
    QDRANT_TIMEOUT_SECONDS: float = 10.0
    DB_TIMEOUT_SECONDS: float = 10.0

    # LangSmith / LangChain Observability & Tracing
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "GraphIntel"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()

# Automatically propagate LangSmith configuration to environment for LangChain/LangGraph
import os
if settings.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true" if settings.LANGCHAIN_TRACING_V2 else "false"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT

# Reload trigger for Google OAuth credentials

