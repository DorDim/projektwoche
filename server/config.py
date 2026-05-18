import os
from dataclasses import dataclass


@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./hardware_monitor.db")
    api_key: str = os.getenv("SERVER_API_KEY", "change-me")
    stale_after_seconds: int = int(os.getenv("STALE_AFTER_SECONDS", "180"))


settings = Settings()
