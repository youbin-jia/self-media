# backend/app/config.py
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
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

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
