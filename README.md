# Projekt: Hardwareueberwachung (Prototyp)

Dieser Prototyp implementiert ein zentrales Monitoring-System fuer Hardwareparameter in einem Rechnernetz.
Er besteht aus:

- **Client-Agent** (`client/agent.py`) zur Erfassung und Uebertragung von Hardwaredaten
- **Server-System** (`server/main.py`) zur Verwaltung, Speicherung (SQL), Auswertung und Visualisierung

## Verwendete Technologien (kostenfrei)

- **Python 3**
- **FastAPI** (REST-API + Webserver)
- **SQLAlchemy** (ORM)
- **SQLite** als Standard (relationale SQL-Datenbank, optional PostgreSQL via `DATABASE_URL`)
- **psutil** fuer Hardware-/Systemdaten
- **Chart.js** fuer Diagramme im Browser

## Architekturuebersicht

1. Client-Agent sammelt Hardwaredaten lokal.
2. Agent registriert sich automatisch am Server (`/api/clients/register`).
3. Agent sendet Snapshots im Intervall an den Server (`/api/clients/{uid}/snapshots`).
4. Server speichert die Daten in SQL-Tabellen:
   - `clients`
   - `hardware_snapshots`
   - `alert_rules`
   - `alert_events`
5. Dashboard zeigt aktuelle + historische Daten und Client-Vergleiche an.
6. Alerts werden bei Regelverletzungen automatisch erzeugt.

## Funktionsabdeckung gemaess Aufgabenstellung

### a) Client-Agent

Erfasst:

- Computername
- CPU (Kerne, Threads, Max-Takt)
- RAM
- GPU (mit Fallbacks)
- Mainboard-Hersteller
- BIOS/UEFI-Hersteller
- Laufwerke (belegt/frei + Prozentwerte)
- Windows-/OS-Version
- Netzwerkadapter
- IP/MAC
- Uptime
- CPU-Temperatur (optional, falls Sensor verfuegbar)
- Luefterdrehzahl (optional, falls Sensor verfuegbar)

Funktionalitaeten:

- Hardwaredaten auslesen (`client/hardware_collector.py`)
- Inventarisierung je Snapshot
- Regelmaessige Datenbereitstellung per Intervall
- Automatische Registrierung beim Server
- Eindeutige Identifikation per stabiler Client-UID

### b) Server-Komponente

- Verwaltung verbundener Clients (inkl. online/offline Status)
- Verarbeitung mehrerer Clients gleichzeitig (HTTP-API)
- Speicherung in relationaler SQL-Datenbank
- Intervallbezug durch periodische Agent-Updates + Stale-Status (`STALE_AFTER_SECONDS`)

### c) Auswertung und Visualisierung

- Web-Dashboard (`/`) mit:
  - Clientliste (aktuelle Werte)
  - Historie pro Client (Diagramm)
  - Vergleich mehrerer Clients
  - Alert-Tabelle

### d) Alarmfunktion (optional)

Implementiert:

- Definierbare Grenzwerte (`/api/alert-rules`)
- Automatische Regelpruefung bei jedem Snapshot
- Erzeugung von Alert-Events mit Meldung
- Standardregel: freier Festplattenspeicher unter 5%

### e) Kommunikation

- Datenaustausch via JSON/HTTP
- Optional absicherbar durch API-Key (`X-API-Key`)
- API-Key wird serverseitig fuer alle `/api`-Endpunkte geprueft

## UML-Diagramme

- UML-Anwendungsfalldiagramm: `docs/uml/anwendungsfalldiagramm.puml`
- UML-Aktivitaetsdiagramm: `docs/uml/aktivitaetsdiagramm.puml`

PlantUML-Dateien koennen z. B. mit VS Code PlantUML Plugin oder PlantUML CLI gerendert werden.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Server starten

```bash
export SERVER_API_KEY="change-me"
export DATABASE_URL="sqlite:///./hardware_monitor.db"
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

Dashboard: `http://localhost:8000`

## Client-Agent starten

```bash
export SERVER_URL="http://127.0.0.1:8000"
export SERVER_API_KEY="change-me"
export AGENT_INTERVAL_SECONDS=60
python -m client.agent
```

## Wichtige Umgebungsvariablen

- `SERVER_API_KEY`: API-Key fuer Server/Client-Kommunikation
- `DATABASE_URL`: SQL-Verbindung (SQLite oder PostgreSQL)
- `STALE_AFTER_SECONDS`: ab wann ein Client als offline gilt
- `AGENT_INTERVAL_SECONDS`: Sendeintervall des Agenten
- `CLIENT_ID_FILE`: Speicherort der lokalen Client-UID

## Beispiel-Endpunkte

- `POST /api/clients/register`
- `POST /api/clients/{client_uid}/snapshots`
- `GET /api/clients`
- `GET /api/clients/{client_uid}/snapshots`
- `GET /api/compare?client_uids=A&client_uids=B`
- `GET /api/alerts`
- `GET /api/alert-rules`
- `POST /api/alert-rules`
- `PATCH /api/alert-rules/{rule_id}`

## Robustheit/Sicherheit/Skalierbarkeit (Prototyp)

- Fehlerbehandlung im Agenten mit Logging + Exponential Backoff
- API-Key-Schutz gegen unbefugten API-Zugriff
- Klare Trennung von Client und Server
- SQL-basierte Persistenz und erweiterbares Datenmodell
- Mehrere Clients koennen parallel Daten senden