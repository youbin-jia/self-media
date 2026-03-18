# backend/app/config.py
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "sqlite:///./data/video_automation.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # API Keys
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    PEXELS_API_KEY: Optional[str] = None

    # Pixabay
    PIXABAY_API_KEY: Optional[str] = None

    # Unsplash
    UNSPLASH_ACCESS_KEY: Optional[str] = None

    # GLM本地模型
    GLM_ENDPOINT: Optional[str] = None

    # LLM配置
    DEFAULT_LLM_PROVIDER: str = "claude"
    LLM_FALLBACK_ENABLED: bool = True

    # Azure Speech
    AZURE_SPEECH_KEY: Optional[str] = None
    AZURE_SPEECH_REGION: Optional[str] = None

    # ElevenLabs
    ELEVENLABS_API_KEY: Optional[str] = None

    # TTS配置
    DEFAULT_TTS_PROVIDER: str = "azure"

    # DALL-E (uses OPENAI_API_KEY, but can override)
    DALLE_API_KEY: Optional[str] = None

    # Midjourney (optional, third-party API)
    MIDJOURNEY_API_KEY: Optional[str] = None
    MIDJOURNEY_ENDPOINT: Optional[str] = None

    # Suno AI (for music generation)
    SUNO_API_KEY: Optional[str] = None
    SUNO_ENDPOINT: Optional[str] = None

    # AI Generation settings
    DEFAULT_AI_GENERATION_PROVIDER: str = "dalle"

    # App Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    API_KEY: str = "your-api-key-change-in-production"

    # JWT Settings
    JWT_SECRET_KEY: str = "your-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_HOURS: int = 168  # 7 days

    # Storage
    DATA_DIR: str = "./data"

    # Cache TTL Configuration (in seconds)
    CACHE_TTL_USER: int = 3600          # 1 hour
    CACHE_TTL_PROJECT: int = 1800       # 30 minutes
    CACHE_TTL_PROJECT_LIST: int = 600   # 10 minutes
    CACHE_TTL_HOT_TOPICS: int = 300     # 5 minutes
    CACHE_TTL_SEARCH: int = 3600        # 1 hour
    CACHE_TTL_DASHBOARD: int = 900      # 15 minutes

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """Validate JWT_SECRET_KEY is changed in production environment."""
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production":
            if "change-in-production" in v or v == "your-jwt-secret-key-change-in-production":
                raise ValueError(
                    "SECURITY ERROR: JWT_SECRET_KEY must be changed from default value in production! "
                    "Set a secure JWT_SECRET_KEY environment variable."
                )
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
