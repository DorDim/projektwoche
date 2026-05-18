import hashlib
import io
import logging
import secrets
import statistics
from csv import DictWriter
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from server.alerts import evaluate_rule, metric_value_for_rule
from server.config import settings
from server.database import Base, engine, get_db
from server.models import AlertEvent, AlertRule, ApiToken, Client, EventLog, HardwareSnapshot, utc_now
from server.schemas import (
    AnomalyOut,
    AlertEventOut,
    AlertRuleIn,
    AlertRuleOut,
    AuthContextOut,
    ClientAnalyticsOut,
    ClientOut,
    ClientSnapshotSummary,
    CompareClientRow,
    EventLogOut,
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
logger = logging.getLogger("hardware-monitor-server")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


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


def log_event(
    db: Session,
    *,
    level: str,
    event_type: str,
    message: str,
    client_uid: str | None = None,
    details: dict | None = None,
):
    db.add(
        EventLog(
            level=level,
            event_type=event_type,
            message=message,
            client_uid=client_uid,
            details=details,
        )
    )


def resolve_auth_context(
    x_api_key: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> dict[str, str | None]:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="fehlender API-Schlüssel")
    if x_api_key == settings.api_key:
        return {"role": "admin", "token_name": "SERVER_API_KEY"}

    token = db.scalar(
        select(ApiToken).where(
            ApiToken.token_hash == hash_token(x_api_key),
            ApiToken.enabled.is_(True),
        )
    )
    if token is None:
        log_event(
            db,
            level="warning",
            event_type="auth_failed",
            message="Ungültiger API-Schlüssel bei Anfrage",
        )
        db.commit()
        raise HTTPException(status_code=401, detail="ungültiger API-Schlüssel")

    return {"role": "user", "token_name": token.name}


def require_api_key(
    auth_context: dict[str, str | None] = Depends(resolve_auth_context),
):
    return auth_context


def require_admin_api_key(auth_context: dict[str, str | None] = Depends(resolve_auth_context)):
    if auth_context["role"] != "admin":
        raise HTTPException(status_code=403, detail="nur mit Admin-API-Schlüssel erlaubt")
    return auth_context


api = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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


def snapshot_min_disk_free(snapshot: HardwareSnapshot) -> float | None:
    return metric_value_for_rule(snapshot, "disk_free_percent_min")


def build_snapshot_export_rows(client: Client, snapshots: list[HardwareSnapshot]) -> list[dict]:
    rows: list[dict] = []
    for snapshot in snapshots:
        rows.append(
            {
                "client_uid": client.client_uid,
                "hostname": snapshot.hostname,
                "collected_at": snapshot.collected_at.isoformat(),
                "os_version": snapshot.os_version,
                "cpu_cores": snapshot.cpu_cores,
                "cpu_threads": snapshot.cpu_threads,
                "cpu_max_mhz": snapshot.cpu_max_mhz,
                "ram_total_mb": snapshot.ram_total_mb,
                "cpu_temperature_c": snapshot.cpu_temperature_c,
                "fan_speed_rpm": snapshot.fan_speed_rpm,
                "uptime_seconds": snapshot.uptime_seconds,
                "motherboard_vendor": snapshot.motherboard_vendor,
                "bios_vendor": snapshot.bios_vendor,
                "min_disk_free_percent": snapshot_min_disk_free(snapshot),
            }
        )
    return rows


def trend_per_hour(values: list[float], timestamps: list[datetime]) -> float | None:
    if len(values) < 2 or len(timestamps) < 2:
        return None
    elapsed_seconds = (timestamps[-1] - timestamps[0]).total_seconds()
    if elapsed_seconds <= 0:
        return None
    return (values[-1] - values[0]) / (elapsed_seconds / 3600)


def analytics_for_snapshots(client_uid: str, snapshots: list[HardwareSnapshot]) -> ClientAnalyticsOut:
    if not snapshots:
        return ClientAnalyticsOut(
            client_uid=client_uid,
            sample_count=0,
            avg_cpu_temperature_c=None,
            avg_disk_free_percent_min=None,
            avg_uptime_seconds=None,
            trend_cpu_temperature_c_per_hour=None,
            trend_disk_free_percent_min_per_hour=None,
            trend_uptime_seconds_per_hour=None,
        )

    ordered = sorted(snapshots, key=lambda item: item.collected_at)
    times = [ensure_utc(snapshot.collected_at) for snapshot in ordered]
    cpu_values = [float(snapshot.cpu_temperature_c) for snapshot in ordered if snapshot.cpu_temperature_c is not None]
    disk_values = [
        float(value)
        for snapshot in ordered
        if (value := snapshot_min_disk_free(snapshot)) is not None
    ]
    uptime_values = [float(snapshot.uptime_seconds) for snapshot in ordered if snapshot.uptime_seconds is not None]

    cpu_points = [(ensure_utc(s.collected_at), float(s.cpu_temperature_c)) for s in ordered if s.cpu_temperature_c is not None]
    disk_points = [
        (ensure_utc(s.collected_at), float(value))
        for s in ordered
        if (value := snapshot_min_disk_free(s)) is not None
    ]
    uptime_points = [(ensure_utc(s.collected_at), float(s.uptime_seconds)) for s in ordered if s.uptime_seconds is not None]

    return ClientAnalyticsOut(
        client_uid=client_uid,
        sample_count=len(ordered),
        avg_cpu_temperature_c=round(statistics.fmean(cpu_values), 3) if cpu_values else None,
        avg_disk_free_percent_min=round(statistics.fmean(disk_values), 3) if disk_values else None,
        avg_uptime_seconds=round(statistics.fmean(uptime_values), 3) if uptime_values else None,
        trend_cpu_temperature_c_per_hour=round(
            trend_per_hour([point[1] for point in cpu_points], [point[0] for point in cpu_points]),
            5,
        )
        if len(cpu_points) >= 2
        else None,
        trend_disk_free_percent_min_per_hour=round(
            trend_per_hour([point[1] for point in disk_points], [point[0] for point in disk_points]),
            5,
        )
        if len(disk_points) >= 2
        else None,
        trend_uptime_seconds_per_hour=round(
            trend_per_hour([point[1] for point in uptime_points], [point[0] for point in uptime_points]),
            5,
        )
        if len(uptime_points) >= 2
        else None,
    )


def detect_anomalies(snapshots: list[HardwareSnapshot]) -> list[AnomalyOut]:
    if not snapshots:
        return []
    ordered = sorted(snapshots, key=lambda item: item.collected_at)
    anomalies: list[AnomalyOut] = []
    previous_uptime: int | None = None

    for snapshot in ordered:
        collected = ensure_utc(snapshot.collected_at)
        min_disk = snapshot_min_disk_free(snapshot)
        if min_disk is not None and min_disk < 10:
            anomalies.append(
                AnomalyOut(
                    collected_at=collected,
                    type="disk_space",
                    severity="high" if min_disk < 5 else "medium",
                    message=f"Kritisch niedriger freier Speicher: {min_disk:.2f}%",
                    value=min_disk,
                    threshold=10.0,
                )
            )

        if snapshot.cpu_temperature_c is not None and snapshot.cpu_temperature_c > 85:
            anomalies.append(
                AnomalyOut(
                    collected_at=collected,
                    type="cpu_temperature",
                    severity="high",
                    message=f"Hohe CPU-Temperatur erkannt: {snapshot.cpu_temperature_c:.2f}°C",
                    value=float(snapshot.cpu_temperature_c),
                    threshold=85.0,
                )
            )

        if previous_uptime is not None and snapshot.uptime_seconds is not None:
            if snapshot.uptime_seconds < previous_uptime * 0.5:
                anomalies.append(
                    AnomalyOut(
                        collected_at=collected,
                        type="uptime_reset",
                        severity="info",
                        message="Möglicher Neustart erkannt (Uptime fiel stark ab).",
                        value=float(snapshot.uptime_seconds),
                        threshold=float(previous_uptime),
                    )
                )
        previous_uptime = snapshot.uptime_seconds if snapshot.uptime_seconds is not None else previous_uptime

    return sorted(anomalies, key=lambda item: item.collected_at, reverse=True)


def get_client_by_uid_or_404(db: Session, client_uid: str) -> Client:
    client = db.scalar(select(Client).where(Client.client_uid == client_uid))
    if client is None:
        raise HTTPException(status_code=404, detail="Client nicht gefunden")
    return client


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


@api.get("/me", response_model=AuthContextOut)
def auth_me(auth_context: dict[str, str | None] = Depends(resolve_auth_context)):
    return AuthContextOut(role=str(auth_context["role"]), token_name=auth_context.get("token_name"))


@api.post("/clients/register", response_model=RegisterClientResponse)
def register_client(payload: RegisterClientRequest, db: Session = Depends(get_db)):
    now = utc_now()
    client = db.scalar(select(Client).where(Client.client_uid == payload.client_uid))
    is_new_client = client is None
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
    log_event(
        db,
        level="info",
        event_type="client_registered" if is_new_client else "client_updated",
        message=f"Client '{payload.client_uid}' wurde {'registriert' if is_new_client else 'aktualisiert'}",
        client_uid=payload.client_uid,
        details={"hostname": payload.hostname, "os_version": payload.os_version},
    )
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
            log_event(
                db,
                level="warning",
                event_type="alert_triggered",
                message=evaluation.message,
                client_uid=client_uid,
                details={"rule_name": rule.name, "metric_value": evaluation.metric_value},
            )
    log_event(
        db,
        level="info",
        event_type="snapshot_ingested",
        message=f"Snapshot gespeichert (id={snapshot.id})",
        client_uid=client_uid,
        details={
            "snapshot_id": snapshot.id,
            "cpu_threads": snapshot.cpu_threads,
            "ram_total_mb": snapshot.ram_total_mb,
            "network_adapter_count": len(snapshot.network_adapters or []),
        },
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
        last_seen = ensure_utc(client.last_seen)
        first_seen = ensure_utc(client.first_seen)
        age = (now - last_seen).total_seconds()
        status = "online" if age <= settings.stale_after_seconds else "offline"
        out.append(
            ClientOut(
                client_uid=client.client_uid,
                hostname=client.hostname,
                os_version=client.os_version,
                first_seen=first_seen,
                last_seen=last_seen,
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
    client = get_client_by_uid_or_404(db, client_uid)
    snapshots = db.scalars(
        select(HardwareSnapshot)
        .where(HardwareSnapshot.client_id == client.id)
        .order_by(HardwareSnapshot.collected_at.desc())
        .limit(limit)
    ).all()
    return [to_snapshot_out(snapshot) for snapshot in snapshots]


@api.get("/clients/{client_uid}/analytics", response_model=ClientAnalyticsOut)
def client_analytics(
    client_uid: str,
    limit: int = Query(default=200, ge=2, le=5000),
    db: Session = Depends(get_db),
):
    client = get_client_by_uid_or_404(db, client_uid)
    snapshots = db.scalars(
        select(HardwareSnapshot)
        .where(HardwareSnapshot.client_id == client.id)
        .order_by(HardwareSnapshot.collected_at.desc())
        .limit(limit)
    ).all()
    return analytics_for_snapshots(client_uid, snapshots)


@api.get("/clients/{client_uid}/anomalies", response_model=list[AnomalyOut])
def client_anomalies(
    client_uid: str,
    limit: int = Query(default=200, ge=2, le=5000),
    db: Session = Depends(get_db),
):
    client = get_client_by_uid_or_404(db, client_uid)
    snapshots = db.scalars(
        select(HardwareSnapshot)
        .where(HardwareSnapshot.client_id == client.id)
        .order_by(HardwareSnapshot.collected_at.desc())
        .limit(limit)
    ).all()
    return detect_anomalies(snapshots)


@api.get("/clients/{client_uid}/export")
def export_client_data(
    client_uid: str,
    export_format: str = Query(default="json", alias="format"),
    limit: int = Query(default=200, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    normalized_format = export_format.lower()
    if normalized_format not in {"json", "csv", "pdf"}:
        raise HTTPException(status_code=422, detail="Format muss json, csv oder pdf sein")

    client = get_client_by_uid_or_404(db, client_uid)
    snapshots = db.scalars(
        select(HardwareSnapshot)
        .where(HardwareSnapshot.client_id == client.id)
        .order_by(HardwareSnapshot.collected_at.desc())
        .limit(limit)
    ).all()

    rows = build_snapshot_export_rows(client, snapshots)

    if normalized_format == "json":
        return JSONResponse(
            content={
                "client_uid": client.client_uid,
                "hostname": client.hostname,
                "snapshot_count": len(rows),
                "snapshots": rows,
            }
        )

    if normalized_format == "csv":
        output = io.StringIO()
        fieldnames = [
            "client_uid",
            "hostname",
            "collected_at",
            "os_version",
            "cpu_cores",
            "cpu_threads",
            "cpu_max_mhz",
            "ram_total_mb",
            "cpu_temperature_c",
            "fan_speed_rpm",
            "uptime_seconds",
            "motherboard_vendor",
            "bios_vendor",
            "min_disk_free_percent",
        ]
        writer = DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        csv_data = output.getvalue()
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{client_uid}-hardware-export.csv"'
            },
        )

    try:
        from fpdf import FPDF
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"PDF-Export nicht verfügbar: {exc}") from exc

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, txt=f"Hardware-Export für {client.hostname} ({client_uid})", ln=True)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 8, txt=f"Snapshots: {len(rows)}", ln=True)
    pdf.ln(2)
    effective_width = getattr(pdf, "epw", 180)
    for row in rows[:200]:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            effective_width,
            6,
            (
                f"{row['collected_at']} | CPU Threads: {row['cpu_threads']} | RAM: {row['ram_total_mb']} MB | "
                f"Disk frei min: {row['min_disk_free_percent']}% | Temp: {row['cpu_temperature_c']}"
            ),
        )
    pdf_bytes = pdf.output(dest="S")
    if isinstance(pdf_bytes, bytearray):
        pdf_bytes = bytes(pdf_bytes)
    elif isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode("latin-1", errors="ignore")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{client_uid}-hardware-export.pdf"'},
    )


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


@api.get("/events", response_model=list[EventLogOut], dependencies=[Depends(require_admin_api_key)])
def list_events(
    level: str | None = None,
    event_type: str | None = None,
    client_uid: str | None = None,
    limit: int = Query(default=300, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    query = select(EventLog)
    if level:
        query = query.where(EventLog.level == level)
    if event_type:
        query = query.where(EventLog.event_type == event_type)
    if client_uid:
        query = query.where(EventLog.client_uid == client_uid)
    query = query.order_by(EventLog.created_at.desc()).limit(limit)
    return db.scalars(query).all()


@api.get("/alert-rules", response_model=list[AlertRuleOut])
def list_alert_rules(db: Session = Depends(get_db)):
    return db.scalars(select(AlertRule).order_by(AlertRule.created_at.asc())).all()


@api.post("/alert-rules", response_model=AlertRuleOut, dependencies=[Depends(require_admin_api_key)])
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
    log_event(
        db,
        level="info",
        event_type="alert_rule_created",
        message=f"Alert-Regel '{payload.name}' erstellt",
        details={
            "metric": payload.metric,
            "comparator": payload.comparator,
            "threshold": payload.threshold,
            "enabled": payload.enabled,
        },
    )
    db.commit()
    db.refresh(rule)
    return rule


@api.patch("/alert-rules/{rule_id}", response_model=AlertRuleOut, dependencies=[Depends(require_admin_api_key)])
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
    log_event(
        db,
        level="info",
        event_type="alert_rule_updated",
        message=f"Alert-Regel '{rule.name}' aktualisiert",
        details={"enabled": rule.enabled, "threshold": rule.threshold},
    )
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
    log_event(
        db,
        level="info",
        event_type="onboarding_token_created",
        message=f"Onboarding-Token '{token_name}' erstellt",
        details={"token_name": token_name},
    )
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
