import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "QuickDrop Rider Payout Dispute Desk"
    DEBUG: bool = True

    # Database Settings (Defaults to local SQLite fallback if Postgres is not running)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./quickdrop_dev.db"
    )
    DATABASE_SYNC_URL: str = os.getenv(
        "DATABASE_SYNC_URL", "sqlite:///./quickdrop_dev.db"
    )

    # PaySwift Base URL
    PAYSWIFT_BASE_URL: str = os.getenv("PAYSWIFT_BASE_URL", "http://localhost:8081")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
