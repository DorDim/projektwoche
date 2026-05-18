import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from server.alerts import evaluate_rule, metric_value_for_rule
from server.config import settings
from server.database import Base, engine, get_db
from server.models import AlertEvent, AlertRule, ApiToken, Client, HardwareSnapshot, utc_now
from server.schemas import (
    AlertEventOut,
    AlertRuleIn,
    AlertRuleOut,
    ClientOut,
    ClientSnapshotSummary,
    CompareClientRow,
    HardwareSnapshotIn,
    OnboardingTokenCreate,
    OnboardingTokenOut,
    RegisterClientRequest,
    RegisterClientResponse,
    SnapshotOut,
)

app = FastAPI(title="Hardwareüberwachung", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def server_origin_and_host(request: Request) -> tuple[str, str]:
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    scheme = forwarded_proto.split(",")[0].strip() if forwarded_proto else request.url.scheme
    host = forwarded_host.split(",")[0].strip() if forwarded_host else request.headers.get("host", "")
    if not host:
        host = request.url.netloc
    return f"{scheme}://{host}", host


def require_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="fehlender API-Schlüssel")
    if x_api_key == settings.api_key:
        return
    token = db.scalar(
        select(ApiToken).where(
            ApiToken.token_hash == hash_token(x_api_key),
            ApiToken.enabled.is_(True),
        )
    )
    if token is None:
        raise HTTPException(status_code=401, detail="ungültiger API-Schlüssel")


def require_admin_api_key(x_api_key: Annotated[str | None, Header()] = None):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="nur mit Admin-API-Schlüssel erlaubt")


api = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


def snapshot_summary(snapshot: HardwareSnapshot | None) -> ClientSnapshotSummary | None:
    if snapshot is None:
        return None
    min_disk_free = metric_value_for_rule(snapshot, "disk_free_percent_min")
    return ClientSnapshotSummary(
        collected_at=snapshot.collected_at,
        cpu_threads=snapshot.cpu_threads,
        ram_total_mb=snapshot.ram_total_mb,
        uptime_seconds=snapshot.uptime_seconds,
        cpu_temperature_c=snapshot.cpu_temperature_c,
        min_disk_free_percent=min_disk_free,
    )


def to_snapshot_out(snapshot: HardwareSnapshot) -> SnapshotOut:
    return SnapshotOut(
        id=snapshot.id,
        collected_at=snapshot.collected_at,
        hostname=snapshot.hostname,
        os_version=snapshot.os_version,
        cpu_cores=snapshot.cpu_cores,
        cpu_threads=snapshot.cpu_threads,
        cpu_max_mhz=snapshot.cpu_max_mhz,
        ram_total_mb=snapshot.ram_total_mb,
        gpu_info=snapshot.gpu_info or [],
        motherboard_vendor=snapshot.motherboard_vendor,
        bios_vendor=snapshot.bios_vendor,
        disks=snapshot.disks or [],
        network_adapters=snapshot.network_adapters or [],
        uptime_seconds=snapshot.uptime_seconds,
        cpu_temperature_c=snapshot.cpu_temperature_c,
        fan_speed_rpm=snapshot.fan_speed_rpm,
    )


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        rule = db.scalar(select(AlertRule).where(AlertRule.name == "disk_free_percent_under_5"))
        if rule is None:
            db.add(
                AlertRule(
                    name="disk_free_percent_under_5",
                    metric="disk_free_percent_min",
                    comparator="lt",
                    threshold=5.0,
                    enabled=True,
                )
            )
            db.commit()


@app.get("/")
def index():
    return FileResponse(static_dir / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc)}


@api.post("/clients/register", response_model=RegisterClientResponse)
def register_client(payload: RegisterClientRequest, db: Session = Depends(get_db)):
    now = utc_now()
    client = db.scalar(select(Client).where(Client.client_uid == payload.client_uid))
    if client is None:
        client = Client(
            client_uid=payload.client_uid,
            hostname=payload.hostname,
            os_version=payload.os_version,
            first_seen=now,
            last_seen=now,
        )
        db.add(client)
    else:
        client.hostname = payload.hostname
        client.os_version = payload.os_version
        client.last_seen = now
    db.commit()
    return RegisterClientResponse(
        client_uid=payload.client_uid, hostname=payload.hostname, registered_at=now
    )


@api.post("/clients/{client_uid}/snapshots")
def ingest_snapshot(client_uid: str, payload: HardwareSnapshotIn, db: Session = Depends(get_db)):
    client = db.scalar(select(Client).where(Client.client_uid == client_uid))
    if client is None:
        raise HTTPException(status_code=404, detail="Client nicht registriert")

    now = utc_now()
    collected_at = payload.collected_at or now
    client.hostname = payload.hostname
    client.os_version = payload.os_version
    client.last_seen = now

    snapshot = HardwareSnapshot(
        client_id=client.id,
        collected_at=collected_at,
        hostname=payload.hostname,
        os_version=payload.os_version,
        cpu_cores=payload.cpu_cores,
        cpu_threads=payload.cpu_threads,
        cpu_max_mhz=payload.cpu_max_mhz,
        ram_total_mb=payload.ram_total_mb,
        gpu_info=[gpu.model_dump() if hasattr(gpu, "model_dump") else gpu for gpu in payload.gpu_info],
        motherboard_vendor=payload.motherboard_vendor,
        bios_vendor=payload.bios_vendor,
        disks=[disk.model_dump() for disk in payload.disks],
        network_adapters=[adapter.model_dump() for adapter in payload.network_adapters],
        uptime_seconds=payload.uptime_seconds,
        cpu_temperature_c=payload.cpu_temperature_c,
        fan_speed_rpm=payload.fan_speed_rpm,
        raw_payload=payload.model_dump(mode="json"),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    alerts_triggered = []
    rules = db.scalars(select(AlertRule).where(AlertRule.enabled.is_(True))).all()
    for rule in rules:
        evaluation = evaluate_rule(rule, snapshot)
        if evaluation.triggered and evaluation.metric_value is not None and evaluation.message:
            event = AlertEvent(
                rule_id=rule.id,
                snapshot_id=snapshot.id,
                client_id=client.id,
                metric_value=evaluation.metric_value,
                message=evaluation.message,
            )
            db.add(event)
            alerts_triggered.append(
                {
                    "rule_name": rule.name,
                    "metric_value": evaluation.metric_value,
                    "message": evaluation.message,
                }
            )
    db.commit()
    return {"snapshot_id": snapshot.id, "alerts": alerts_triggered}


@api.get("/clients", response_model=list[ClientOut])
def list_clients(db: Session = Depends(get_db)):
    now = utc_now()
    clients = db.scalars(select(Client).order_by(Client.hostname.asc())).all()
    out: list[ClientOut] = []
    for client in clients:
        latest = db.scalar(
            select(HardwareSnapshot)
            .where(HardwareSnapshot.client_id == client.id)
            .order_by(HardwareSnapshot.collected_at.desc())
            .limit(1)
        )
        age = (now - client.last_seen).total_seconds()
        status = "online" if age <= settings.stale_after_seconds else "offline"
        out.append(
            ClientOut(
                client_uid=client.client_uid,
                hostname=client.hostname,
                os_version=client.os_version,
                first_seen=client.first_seen,
                last_seen=client.last_seen,
                status=status,
                latest_snapshot=snapshot_summary(latest),
            )
        )
    return out


@api.get("/clients/{client_uid}/snapshots", response_model=list[SnapshotOut])
def list_snapshots(
    client_uid: str,
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    client = db.scalar(select(Client).where(Client.client_uid == client_uid))
    if client is None:
        raise HTTPException(status_code=404, detail="Client nicht gefunden")
    snapshots = db.scalars(
        select(HardwareSnapshot)
        .where(HardwareSnapshot.client_id == client.id)
        .order_by(HardwareSnapshot.collected_at.desc())
        .limit(limit)
    ).all()
    return [to_snapshot_out(snapshot) for snapshot in snapshots]


@api.get("/compare", response_model=list[CompareClientRow])
def compare_clients(client_uids: list[str] = Query(default=[]), db: Session = Depends(get_db)):
    rows: list[CompareClientRow] = []
    for client_uid in client_uids:
        client = db.scalar(select(Client).where(Client.client_uid == client_uid))
        if client is None:
            continue
        latest = db.scalar(
            select(HardwareSnapshot)
            .where(HardwareSnapshot.client_id == client.id)
            .order_by(HardwareSnapshot.collected_at.desc())
            .limit(1)
        )
        rows.append(
            CompareClientRow(
                client_uid=client.client_uid,
                hostname=client.hostname,
                cpu_threads=latest.cpu_threads if latest else None,
                ram_total_mb=latest.ram_total_mb if latest else None,
                min_disk_free_percent=metric_value_for_rule(latest, "disk_free_percent_min")
                if latest
                else None,
                uptime_seconds=latest.uptime_seconds if latest else None,
            )
        )
    return rows


@api.get("/alerts", response_model=list[AlertEventOut])
def list_alerts(
    client_uid: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    events_query = select(AlertEvent).order_by(AlertEvent.triggered_at.desc()).limit(limit)
    if client_uid:
        client = db.scalar(select(Client).where(Client.client_uid == client_uid))
        if client is None:
            return []
        events_query = (
            select(AlertEvent)
            .where(AlertEvent.client_id == client.id)
            .order_by(AlertEvent.triggered_at.desc())
            .limit(limit)
        )

    events = db.scalars(events_query).all()
    out: list[AlertEventOut] = []
    for event in events:
        out.append(
            AlertEventOut(
                id=event.id,
                client_uid=event.client.client_uid,
                rule_name=event.rule.name,
                metric_value=event.metric_value,
                message=event.message,
                triggered_at=event.triggered_at,
            )
        )
    return out


@api.get("/alert-rules", response_model=list[AlertRuleOut])
def list_alert_rules(db: Session = Depends(get_db)):
    return db.scalars(select(AlertRule).order_by(AlertRule.created_at.asc())).all()


@api.post("/alert-rules", response_model=AlertRuleOut)
def create_alert_rule(payload: AlertRuleIn, db: Session = Depends(get_db)):
    existing = db.scalar(select(AlertRule).where(AlertRule.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Regelname bereits vorhanden")
    if payload.comparator not in {"lt", "gt"}:
        raise HTTPException(status_code=422, detail="Comparator muss lt oder gt sein")
    rule = AlertRule(
        name=payload.name,
        metric=payload.metric,
        comparator=payload.comparator,
        threshold=payload.threshold,
        enabled=payload.enabled,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@api.patch("/alert-rules/{rule_id}", response_model=AlertRuleOut)
def update_alert_rule(
    rule_id: int,
    enabled: bool | None = None,
    threshold: float | None = None,
    db: Session = Depends(get_db),
):
    rule = db.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Regel nicht gefunden")
    if enabled is not None:
        rule.enabled = enabled
    if threshold is not None:
        rule.threshold = threshold
    db.commit()
    db.refresh(rule)
    return rule


@api.post(
    "/onboarding-tokens",
    response_model=OnboardingTokenOut,
    dependencies=[Depends(require_admin_api_key)],
)
def create_onboarding_token(
    payload: OnboardingTokenCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    token_value = secrets.token_urlsafe(32)
    token_name = payload.name or f"Client-Token-{int(datetime.now(timezone.utc).timestamp())}"
    api_token = ApiToken(name=token_name, token_hash=hash_token(token_value), enabled=True)
    db.add(api_token)
    db.commit()
    db.refresh(api_token)
    origin, host = server_origin_and_host(request)
    return OnboardingTokenOut(
        name=api_token.name,
        token=token_value,
        created_at=api_token.created_at,
        server_origin=origin,
        server_host=host,
    )


app.include_router(api)
