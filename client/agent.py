import json
import logging
import time
from pathlib import Path

import requests

from client.config import settings
from client.hardware_collector import collect_snapshot, get_client_uid, get_hostname, get_windows_version

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("hardware-agent")


def _headers() -> dict[str, str]:
    return {"X-API-Key": settings.api_key, "Content-Type": "application/json"}


def _client_id_path() -> Path:
    return Path(settings.client_id_file).resolve()


def load_or_create_client_uid() -> str:
    path = _client_id_path()
    if path.exists():
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            content = {}
        stored = content.get("client_uid")
        if stored:
            return stored

    client_uid = get_client_uid()
    payload = {"client_uid": client_uid}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return client_uid


def register_client(session: requests.Session, client_uid: str) -> None:
    response = session.post(
        f"{settings.server_url}/api/clients/register",
        json={
            "client_uid": client_uid,
            "hostname": get_hostname(),
            "os_version": get_windows_version(),
        },
        headers=_headers(),
        timeout=settings.request_timeout_seconds,
    )
    response.raise_for_status()
    logger.info("Client registriert: %s", client_uid)


def send_snapshot(session: requests.Session, client_uid: str) -> None:
    snapshot = collect_snapshot()
    response = session.post(
        f"{settings.server_url}/api/clients/{client_uid}/snapshots",
        json=snapshot,
        headers=_headers(),
        timeout=settings.request_timeout_seconds,
    )
    response.raise_for_status()
    body = response.json()
    alerts = body.get("alerts", [])
    if alerts:
        for alert in alerts:
            logger.warning("Alarm: %s", alert.get("message"))
    else:
        logger.info("Snapshot gespeichert (id=%s)", body.get("snapshot_id"))


def run_agent():
    client_uid = load_or_create_client_uid()
    session = requests.Session()
    backoff = 2

    while True:
        try:
            register_client(session, client_uid)
            send_snapshot(session, client_uid)
            backoff = 2
            time.sleep(settings.interval_seconds)
        except requests.RequestException as exc:
            logger.error("Verbindung/HTTP-Fehler: %s", exc)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unerwarteter Fehler: %s", exc)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    run_agent()
