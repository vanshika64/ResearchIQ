from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Port and Environment
    PORT: int = Field(default=8000)
    ENVIRONMENT: str = Field(default="development")

    # Supabase Settings
    SUPABASE_URL: str = Field(default="https://placeholder-id.supabase.co")
    SUPABASE_ANON_KEY: str = Field(default="placeholder-anon-key")
    SUPABASE_SERVICE_KEY: Optional[str] = Field(default=None)
    FRONTEND_URL: str = Field(default="https://research-iq1.streamlit.app")

    # Database Settings
    # Fallback to local SQLite for easy local validation if DATABASE_URL is not set
    DATABASE_URL: str = Field(default="sqlite:///./researchiq.db")

    # AWS S3 Settings
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None)
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None)
    AWS_REGION: str = Field(default="us-east-1")
    AWS_S3_BUCKET: Optional[str] = Field(default=None)

    # Local Storage Fallback
    LOCAL_STORAGE_DIR: str = Field(default="./local_storage")

    # LLM Settings
    LLM_PROVIDER: str = Field(default="groq")
    GROQ_API_KEY: Optional[str] = Field(default=None)
    
    # Model configuration
    LLM_MODEL: str = Field(default="qwen/qwen3.8-27b")
    LLM_TEMPERATURE: float = Field(default=0.2)

    # Embeddings Configuration
    # openai, gemini, huggingface
    EMBEDDINGS_PROVIDER: str = Field(default="huggingface")
    EMBEDDINGS_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    HF_LOCAL_FILES_ONLY: bool = Field(default=False)

    # Vector Store Settings
    VECTOR_STORE_PROVIDER: str = Field(default="faiss")  # faiss, chroma
    VECTOR_STORE_DIR: str = Field(default="./vector_stores")

    # RAG Settings
    RAG_CHUNK_SIZE: int = Field(default=1000)
    RAG_CHUNK_OVERLAP: int = Field(default=200)
    RAG_TOP_K: int = Field(default=4)

    # JWT Authentication
    JWT_SECRET: str = Field(default="researchiq-backend-secret-super-key")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)

    # CORS Origin Settings
    CORS_ORIGINS: str = Field(
        default="https://research-iq1.streamlit.app,http://localhost:8501,http://127.0.0.1:8501"
    )

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
