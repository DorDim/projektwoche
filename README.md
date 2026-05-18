# Projekt: Hardwareüberwachung (Prototyp)

Dieser Prototyp implementiert ein zentrales Monitoring-System für Hardwareparameter in einem Rechnernetz.
Er besteht aus:

- **Client-Agent** (`client/agent.py`) zur Erfassung und Übertragung von Hardwaredaten
- **Server-System** (`server/main.py`) zur Verwaltung, Speicherung (SQL), Auswertung und Visualisierung

## Verwendete Technologien (kostenfrei)

- **Python 3**
- **FastAPI** (REST-API + Webserver)
- **SQLAlchemy** (ORM)
- **SQLite** als Standard (relationale SQL-Datenbank, optional externe PostgreSQL via `DATABASE_URL`)
- **psutil** für Hardware-/Systemdaten
- **Chart.js** für Diagramme
- **Tailwind CSS** für das Web-Interface

## Architekturübersicht

1. Client-Agent sammelt Hardwaredaten lokal.
2. Agent registriert sich automatisch am Server (`/api/clients/register`).
3. Agent sendet Snapshots im Intervall an den Server (`/api/clients/{uid}/snapshots`).
4. Server speichert die Daten in SQL-Tabellen:
   - `clients`
   - `hardware_snapshots`
   - `alert_rules`
   - `alert_events`
   - `api_tokens`
5. Dashboard zeigt aktuelle + historische Daten und Client-Vergleiche an.
6. Alerts werden bei Regelverletzungen automatisch erzeugt.

## Neues Web-Feature: „Neuen Client hinzufügen“

Im Dashboard gibt es den Button **„Neuen Client hinzufügen“**.  
Darüber erhältst du:

- automatisch generierten Client-Token
- erkannte Server-URL + IP/Domain
- Schritt-für-Schritt-Anleitung
- sofort kopierbare Beispielbefehle für den Agent-Start

Der Token wird über `POST /api/onboarding-tokens` erzeugt (nur mit Admin-API-Key).

## UML-Diagramme

- UML-Anwendungsfalldiagramm: `docs/uml/anwendungsfalldiagramm.puml`
- UML-Aktivitätsdiagramm: `docs/uml/aktivitaetsdiagramm.puml`

PlantUML-Dateien können z. B. mit VS Code PlantUML Plugin oder PlantUML CLI gerendert werden.

## Installation (lokal ohne Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
npm run build:css
```

## Server als Docker Compose (empfohlen)

1. Konfiguration vorbereiten:

```bash
cp .env.example .env
```

2. Stack starten (Server + PostgreSQL):

```bash
docker compose up -d --build
```

3. Prüfen:

```bash
docker compose ps
docker compose logs -f server
```

Dashboard: `http://localhost:8000`

Stoppen:

```bash
docker compose down
```

Komplett zurücksetzen (inkl. DB-Daten):

```bash
docker compose down -v
```

## Server manuell starten

```bash
export SERVER_API_KEY="change-me"
export DATABASE_URL="sqlite:///./hardware_monitor.db"
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

Hinweis zum Frontend: Die Oberfläche nutzt eine lokal gebaute Tailwind-Datei (`server/static/tailwind.css`).
Nach Änderungen an `server/static/index.html` oder `server/static/app.js` bitte neu bauen:

```bash
npm run build:css
```

## Client-Agent starten

```bash
export SERVER_URL="http://127.0.0.1:8000"
export SERVER_API_KEY="change-me"
export AGENT_INTERVAL_SECONDS=60
python -m client.agent
```

## Wichtige Umgebungsvariablen

- `SERVER_API_KEY`: Admin-API-Key für Server/Client-Kommunikation
- `DATABASE_URL`: SQL-Verbindung (SQLite oder PostgreSQL)
- `DB_SSLMODE`: optionaler SSL-Modus für PostgreSQL (`require`, `verify-ca`, `verify-full`, ...)
- `DB_POOL_SIZE`: Größe des DB-Verbindungspools (Standard `10`)
- `DB_MAX_OVERFLOW`: zusätzliche Burst-Verbindungen außerhalb des Pools (Standard `20`)
- `STALE_AFTER_SECONDS`: ab wann ein Client als offline gilt
- `AGENT_INTERVAL_SECONDS`: Sendeintervall des Agenten
- `CLIENT_ID_FILE`: Speicherort der lokalen Client-UID

## Externe PostgreSQL-Datenbank (optional)

Du kannst statt SQLite eine externe PostgreSQL-Instanz verwenden, z. B. in Cloud/Hosting:

```bash
export SERVER_API_KEY="change-me"
export DATABASE_URL="postgres://monitor_user:strongpass@db.example.com:5432/hardware_monitor"
export DB_SSLMODE="require"
uvicorn server.main:app --host 0.0.0.0 --port 8000
```

Hinweise:
- `postgres://...` und `postgresql://...` werden automatisch auf das SQLAlchemy-Format normalisiert.
- Für produktive externe DBs sollte TLS/SSL aktiviert sein (`DB_SSLMODE=require`).
- Tabellen werden beim Server-Start automatisch erstellt (Prototyp-Verhalten).

Auch mit Docker Compose möglich:

```bash
cp .env.example .env
# DATABASE_URL in .env auf externe DB setzen
# optional: DB_SSLMODE=require setzen
docker compose up -d --build server
```

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
- `POST /api/onboarding-tokens`

## Robustheit, Sicherheit, Skalierbarkeit (Prototyp)

- Fehlerbehandlung im Agenten mit Logging + Exponential Backoff
- API-Key-Schutz gegen unbefugten API-Zugriff
- Zusätzliche pro-Client API-Tokens für Onboarding
- Klare Trennung von Client und Server
- SQL-basierte Persistenz und erweiterbares Datenmodell
- Mehrere Clients können parallel Daten senden