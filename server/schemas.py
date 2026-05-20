from datetime import date, datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


PASSWORD_SPECIAL_CHAR_PATTERN = re.compile(r"[^A-Za-z0-9]")


def validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Passwort muss mindestens 8 Zeichen lang sein")
    if PASSWORD_SPECIAL_CHAR_PATTERN.search(value) is None:
        raise ValueError("Passwort muss mindestens ein Sonderzeichen enthalten")
    return value


class DiskInfo(BaseModel):
    mountpoint: str
    filesystem: str | None = None
    total_gb: float
    used_gb: float
    free_gb: float
    free_percent: float


class NetworkAdapter(BaseModel):
    name: str
    ipv4: list[str] = Field(default_factory=list)
    ipv6: list[str] = Field(default_factory=list)
    mac: str | None = None


class RegisterClientRequest(BaseModel):
    client_uid: str
    hostname: str
    os_version: str | None = None


class RegisterClientResponse(BaseModel):
    client_uid: str
    hostname: str
    registered_at: datetime


class HardwareSnapshotIn(BaseModel):
    hostname: str
    os_version: str | None = None
    collected_at: datetime | None = None
    cpu_cores: int | None = None
    cpu_threads: int | None = None
    cpu_max_mhz: float | None = None
    ram_total_mb: float | None = None
    gpu_info: list[dict] = Field(default_factory=list)
    motherboard_vendor: str | None = None
    bios_vendor: str | None = None
    disks: list[DiskInfo] = Field(default_factory=list)
    network_adapters: list[NetworkAdapter] = Field(default_factory=list)
    uptime_seconds: int | None = None


class AlertRuleIn(BaseModel):
    name: str
    metric: str
    comparator: str
    threshold: float
    enabled: bool = True


class AlertRuleOut(AlertRuleIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class AlertEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    client_uid: str
    rule_name: str
    metric_value: float
    message: str
    triggered_at: datetime


class ClientSnapshotSummary(BaseModel):
    collected_at: datetime
    cpu_threads: int | None
    ram_total_mb: float | None
    uptime_seconds: int | None
    min_disk_free_percent: float | None


class ClientOut(BaseModel):
    client_uid: str
    hostname: str
    os_version: str | None
    first_seen: datetime
    last_seen: datetime
    status: str
    location: str | None = None
    asset_tag: str | None = None
    serial_number: str | None = None
    department: str | None = None
    responsible_person: str | None = None
    supplier: str | None = None
    purchase_date: date | None = None
    purchase_price_eur: float | None = None
    warranty_until: date | None = None
    notes: str | None = None
    latest_snapshot: ClientSnapshotSummary | None


class SnapshotOut(BaseModel):
    id: int
    collected_at: datetime
    hostname: str
    os_version: str | None
    cpu_cores: int | None
    cpu_threads: int | None
    cpu_max_mhz: float | None
    ram_total_mb: float | None
    gpu_info: list[dict]
    motherboard_vendor: str | None
    bios_vendor: str | None
    disks: list[DiskInfo]
    network_adapters: list[NetworkAdapter]
    uptime_seconds: int | None


class CompareClientRow(BaseModel):
    client_uid: str
    hostname: str
    cpu_threads: int | None
    ram_total_mb: float | None
    min_disk_free_percent: float | None
    uptime_seconds: int | None


class ClientInventoryUpdateIn(BaseModel):
    location: str | None = None
    asset_tag: str | None = None
    serial_number: str | None = None
    department: str | None = None
    responsible_person: str | None = None
    supplier: str | None = None
    purchase_date: date | None = None
    purchase_price_eur: float | None = None
    warranty_until: date | None = None
    notes: str | None = None

    @field_validator("purchase_price_eur")
    @classmethod
    def validate_purchase_price(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value < 0:
            raise ValueError("Anschaffungspreis darf nicht negativ sein")
        return value


class OnboardingTokenCreate(BaseModel):
    name: str | None = None


class OnboardingTokenOut(BaseModel):
    name: str
    token: str
    created_at: datetime
    server_origin: str
    server_host: str


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    role: str
    token_name: str
    username: str


class AuthContextOut(BaseModel):
    username: str
    role: str
    permissions: dict[str, bool]
    token_name: str | None = None


class ClientAnalyticsOut(BaseModel):
    client_uid: str
    sample_count: int
    avg_disk_free_percent_min: float | None
    avg_uptime_seconds: float | None
    trend_disk_free_percent_min_per_hour: float | None
    trend_uptime_seconds_per_hour: float | None


class AnomalyOut(BaseModel):
    collected_at: datetime
    type: str
    severity: str
    message: str
    value: float | None = None
    threshold: float | None = None


class EventLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    level: str
    event_type: str
    message: str
    client_uid: str | None
    details: dict | None


class UserCreateIn(BaseModel):
    username: str
    password: str
    role: str = "user"
    permissions: dict[str, bool] = Field(default_factory=dict)
    is_active: bool = True

    @field_validator("password")
    @classmethod
    def password_policy(cls, value: str) -> str:
        return validate_password_strength(value)


class UserUpdateIn(BaseModel):
    password: str | None = None
    role: str | None = None
    permissions: dict[str, bool] | None = None
    is_active: bool | None = None

    @field_validator("password")
    @classmethod
    def optional_password_policy(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_password_strength(value)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    permissions: dict[str, bool] | None = None
    is_active: bool
    created_at: datetime
