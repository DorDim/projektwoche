from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    cpu_temperature_c: float | None = None
    fan_speed_rpm: int | None = None


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
    cpu_temperature_c: float | None
    min_disk_free_percent: float | None


class ClientOut(BaseModel):
    client_uid: str
    hostname: str
    os_version: str | None
    first_seen: datetime
    last_seen: datetime
    status: str
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
    cpu_temperature_c: float | None
    fan_speed_rpm: int | None


class CompareClientRow(BaseModel):
    client_uid: str
    hostname: str
    cpu_threads: int | None
    ram_total_mb: float | None
    min_disk_free_percent: float | None
    uptime_seconds: int | None


class OnboardingTokenCreate(BaseModel):
    name: str | None = None


class OnboardingTokenOut(BaseModel):
    name: str
    token: str
    created_at: datetime
    server_origin: str
    server_host: str


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str
    role: str
    token_name: str


class AuthContextOut(BaseModel):
    role: str
    token_name: str | None = None


class ClientAnalyticsOut(BaseModel):
    client_uid: str
    sample_count: int
    avg_cpu_temperature_c: float | None
    avg_disk_free_percent_min: float | None
    avg_uptime_seconds: float | None
    trend_cpu_temperature_c_per_hour: float | None
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
