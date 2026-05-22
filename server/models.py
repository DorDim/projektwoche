"""ORM-Modelle fuer Monitoring-, Inventar-, Auth- und Event-Daten."""

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.database import Base


def utc_now() -> datetime:
    """Erzeugt einen konsistenten UTC-Zeitstempel fuer Defaults."""
    return datetime.now(timezone.utc)


class Client(Base):
    """Stammdaten eines registrierten Clients inklusive Inventarfeldern."""
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_uid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    hostname: Mapped[str] = mapped_column(String(255), index=True)
    os_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    asset_tag: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    responsible_person: Mapped[str | None] = mapped_column(String(128), nullable=True)
    supplier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_price_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    warranty_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    snapshots: Mapped[list["HardwareSnapshot"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["AlertEvent"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )


class HardwareSnapshot(Base):
    """Zeitpunktbezogene technische Messdaten eines Clients."""
    __tablename__ = "hardware_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    hostname: Mapped[str] = mapped_column(String(255), index=True)
    os_version: Mapped[str | None] = mapped_column(String(255), nullable=True)

    cpu_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_threads: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_max_mhz: Mapped[float | None] = mapped_column(Float, nullable=True)
    ram_total_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    gpu_info: Mapped[list | None] = mapped_column(JSON, nullable=True)
    motherboard_vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bios_vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    disks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    network_adapters: Mapped[list | None] = mapped_column(JSON, nullable=True)
    uptime_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="snapshots")
    alerts: Mapped[list["AlertEvent"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class AlertRule(Base):
    """Konfigurierbare Regeldefinition fuer Schwellenwertpruefungen."""
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    metric: Mapped[str] = mapped_column(String(64), index=True)
    comparator: Mapped[str] = mapped_column(String(8))
    threshold: Mapped[float] = mapped_column(Float)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    alerts: Mapped[list["AlertEvent"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class AlertEvent(Base):
    """Ausgeloester Alert inklusive Regel-, Snapshot- und Client-Bezug."""
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id"), index=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("hardware_snapshots.id"), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    message: Mapped[str] = mapped_column(Text)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    rule: Mapped["AlertRule"] = relationship(back_populates="alerts")
    snapshot: Mapped["HardwareSnapshot"] = relationship(back_populates="alerts")
    client: Mapped["Client"] = relationship(back_populates="alerts")


class ApiToken(Base):
    """Persistierte API-Tokens fuer Agenten/Onboarding (nur gehashter Token)."""
    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AppUser(Base):
    """Interner Web-Benutzer mit Rolle, Rechten und Aktiv-Status."""
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="user")
    permissions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    """Login-Session eines Benutzers (gehashter Sitzungstoken)."""
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["AppUser"] = relationship(back_populates="sessions")


class EventLog(Base):
    """Audit-/Betriebsprotokoll fuer relevante System- und Benutzeraktionen."""
    __tablename__ = "event_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    level: Mapped[str] = mapped_column(String(16), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    client_uid: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
