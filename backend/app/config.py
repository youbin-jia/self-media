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
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo"
    KIMI_API_KEY: Optional[str] = None
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"
    KIMI_MODEL: str = "moonshot-v1-8k"
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

    # Aliyun NLS TTS
    ALIYUN_ACCESS_KEY_ID: Optional[str] = None
    ALIYUN_ACCESS_KEY_SECRET: Optional[str] = None
    ALIYUN_TTS_TOKEN: Optional[str] = None
    ALIYUN_TTS_APP_KEY: Optional[str] = None
    ALIYUN_TTS_REGION: str = "cn-shanghai"
    ALIYUN_TTS_VOICE: str = "xiaoyun"

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

    # 通义万相 Wan2.1 图生视频（本地 generate.py 或 HTTP 侧车，见 docs/WAN2.1_LOCAL.md）
    WAN_I2V_ENABLED: bool = False
    # subprocess：在本机执行 Wan-Video/Wan2.1 的 generate.py | http：调用侧车
    WAN_I2V_MODE: str = "subprocess"
    WAN_I2V_ENDPOINT: Optional[str] = None
    WAN_I2V_HTTP_BEARER: Optional[str] = None
    WAN_I2V_REPO_DIR: Optional[str] = None
    WAN_I2V_CKPT_DIR: Optional[str] = None
    WAN_I2V_PYTHON: str = "python"
    WAN_I2V_TASK: str = "i2v-14B"
    WAN_I2V_SIZE: str = "1280*720"
    WAN_I2V_EXTRA_ARGS: str = ""
    WAN_I2V_TIMEOUT_SEC: int = 7200

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

    # Celery Configuration
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_TASK_REJECT_ON_WORKER_LOST: bool = True
    CELERY_TASK_RESULT_CACHE_TTL: int = 3600  # 1 hour default cache TTL for tasks

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
