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
    PEXELS_API_KEY: Optional[str] = None

    # App Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    API_KEY: str = "your-api-key-change-in-production"

    # Storage
    DATA_DIR: str = "./data"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
