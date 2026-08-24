from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Distributed Job Scheduler"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/jobscheduler"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    
    # JWT Security
    JWT_SECRET: str = "404E635266556A586E3272357538782F413F4428472B4B6250645367566B5970"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Worker & Scheduling Engine Defaults
    WORKER_ID: str = "worker-auto"
    WORKER_ENABLED: bool = True
    WORKER_CONCURRENCY: int = 5
    POLLING_INTERVAL_MS: int = 1000
    HEARTBEAT_INTERVAL_MS: int = 5000
    HEARTBEAT_TIMEOUT_MS: int = 30000
    CLAIM_BATCH_SIZE: int = 5
    WORKER_SHUTDOWN_TIMEOUT_SECONDS: int = 30
    
    # Supervisor / Reaper / Cron intervals
    REAPER_ENABLED: bool = True
    REAPER_INTERVAL_MS: int = 10000
    CRON_ENABLED: bool = True
    CRON_INTERVAL_MS: int = 5000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
