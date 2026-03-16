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

    # App Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    API_KEY: str = "your-api-key-change-in-production"

    # Storage
    DATA_DIR: str = "./data"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
