import os
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./hardware_monitor.db")
    api_key: str = os.getenv("SERVER_API_KEY", "change-me")
    start_admin_password: str | None = os.getenv("START_ADMIN_PASSWORD")
    stale_after_seconds: int = int(os.getenv("STALE_AFTER_SECONDS", "180"))
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    db_sslmode: str | None = os.getenv("DB_SSLMODE")

    @property
    def normalized_database_url(self) -> str:
        url = self.database_url.strip()

        # Support common "postgres://" format by normalizing to SQLAlchemy dialect URL.
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://") :]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]

        if self.db_sslmode and url.startswith("postgresql+psycopg://"):
            parts = urlsplit(url)
            query = dict(parse_qsl(parts.query, keep_blank_values=True))
            query.setdefault("sslmode", self.db_sslmode)
            url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

        return url


settings = Settings()
