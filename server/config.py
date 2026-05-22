"""Zentrale Laufzeitkonfiguration aus Umgebungsvariablen."""

import os
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _env_bool(name: str, default: str = "false") -> bool:
    """Wandelt typische Wahr/Falsch-Strings aus der Umgebung in bool um."""
    value = os.getenv(name, default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "").strip()
    api_key: str = os.getenv("SERVER_API_KEY", "change-me")
    start_admin_password: str | None = os.getenv("START_ADMIN_PASSWORD")
    start_admin_username: str = os.getenv("START_ADMIN_USERNAME", "admin")
    stale_after_seconds: int = int(os.getenv("STALE_AFTER_SECONDS", "180"))
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    db_sslmode: str | None = os.getenv("DB_SSLMODE")
    log_data_access_events: bool = _env_bool("LOG_DATA_ACCESS_EVENTS", "false")
    enable_demo_data: bool = _env_bool("ENABLE_DEMO_DATA", "true")
    demo_username: str = os.getenv("DEMO_USERNAME", "demo")
    demo_password: str = os.getenv("DEMO_PASSWORD", "Demo!123")
    demo_client_count: int = int(os.getenv("DEMO_CLIENT_COUNT", "6"))
    demo_snapshot_interval_seconds: int = int(os.getenv("DEMO_SNAPSHOT_INTERVAL_SECONDS", "60"))

    @property
    def normalized_database_url(self) -> str:
        # Im Compose-Betrieb kann DATABASE_URL leer bleiben und aus POSTGRES_* gebaut werden.
        url = self.database_url.strip()
        if not url:
            pg_user = os.getenv("POSTGRES_USER", "monitor_user").strip() or "monitor_user"
            pg_password = os.getenv("POSTGRES_PASSWORD", "monitor_password")
            pg_db = os.getenv("POSTGRES_DB", "hardware_monitor").strip() or "hardware_monitor"
            pg_host = os.getenv("POSTGRES_HOST", "postgres").strip() or "postgres"
            pg_port = os.getenv("POSTGRES_PORT", "5432").strip() or "5432"
            url = f"postgresql+psycopg://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

        # Uebliche postgres:// Varianten auf das SQLAlchemy-Dialektformat normalisieren.
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://") :]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]

        if url.startswith("sqlite"):
            raise ValueError("SQLite wird nicht mehr unterstützt. Bitte PostgreSQL über DATABASE_URL konfigurieren.")
        if not url.startswith("postgresql+psycopg://"):
            raise ValueError(
                "Ungültige DATABASE_URL. Erwartet wird ein PostgreSQL-URL im Format postgresql+psycopg://..."
            )

        if self.db_sslmode and url.startswith("postgresql+psycopg://"):
            # Bereits gesetzte Query-Parameter beibehalten und sslmode nur ergaenzen.
            parts = urlsplit(url)
            query = dict(parse_qsl(parts.query, keep_blank_values=True))
            query.setdefault("sslmode", self.db_sslmode)
            url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

        return url


settings = Settings()
