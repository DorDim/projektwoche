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
   - `app_users`
   - `user_sessions`
5. Dashboard zeigt aktuelle + historische Daten und Client-Vergleiche an.
6. Alerts werden bei Regelverletzungen automatisch erzeugt.

## Neues Web-Feature: „Neuen Client hinzufügen“

Im Dashboard gibt es den Button **„Neuen Client hinzufügen“**.  
Darüber erhältst du:

- automatisch generierten Client-Token
- erkannte Server-URL + IP/Domain
- Schritt-für-Schritt-Anleitung
- sofort kopierbare Beispielbefehle für den Agent-Start

Der Token wird über `POST /api/onboarding-tokens` erzeugt (Berechtigung `add_clients`).

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

2. `.env` anpassen (Traefik + Zertifikate):

```env
TRAEFIK_DOMAIN=monitor.example.com
TRAEFIK_ACME_EMAIL=admin@example.com
TRAEFIK_DOCKER_API_VERSION=1.41
```

Wichtig:
- DNS `A`/`AAAA` Record der Domain muss auf deinen Server zeigen.
- Ports `80` und `443` müssen von außen erreichbar sein.
- Falls Traefik meldet `client version 1.24 is too old`, setze `TRAEFIK_DOCKER_API_VERSION=1.41`.

3. Stack starten (Traefik + Server + PostgreSQL):

```bash
docker compose up -d --build
```

4. Prüfen:

```bash
docker compose ps
docker compose logs -f traefik
docker compose logs -f server
```

Dashboard: `https://DEINE_DOMAIN`  
Vergleichsseite: `https://DEINE_DOMAIN/compare`  
Nutzerverwaltung: `https://DEINE_DOMAIN/users`

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
export START_ADMIN_USERNAME="admin"
export START_ADMIN_PASSWORD="changeme-admin-password"
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

## Client-Agent im Hintergrund (Windows, empfohlen)

Der Agent kann als geplanter Task laufen, damit kein Terminal offen bleiben muss.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "git clone https://github.com/DorDim/projektwoche.git; cd projektwoche; powershell -ExecutionPolicy Bypass -File .\client\install_windows_background.ps1 -ServerUrl 'http://DEIN-SERVER:8000' -ApiKey 'DEIN_TOKEN_ODER_SERVER_API_KEY' -IntervalSeconds 60 -StartNow"
```

Task prüfen:

```powershell
Get-ScheduledTask -TaskName "HardwareMonitorClientAgent"
```

Task entfernen:

```powershell
Unregister-ScheduledTask -TaskName "HardwareMonitorClientAgent" -Confirm:$false
```

## Client-Agent im Hintergrund (Linux, Ein-Befehl)

```bash
bash -lc 'git clone https://github.com/DorDim/projektwoche.git && cd projektwoche && bash ./client/install_linux_background.sh --server-url "http://DEIN-SERVER:8000" --api-key "DEIN_TOKEN_ODER_SERVER_API_KEY" --interval-seconds 60'
```

Status prüfen:

```bash
systemctl --user status hardware-monitor-client-agent.service
```

Entfernen:

```bash
systemctl --user disable --now hardware-monitor-client-agent.service
```

## Wichtige Umgebungsvariablen

- `SERVER_API_KEY`: Admin-API-Key für Server/Client-Kommunikation
- `START_ADMIN_USERNAME`: Benutzername für den initialen Admin (Standard `admin`)
- `START_ADMIN_PASSWORD`: Passwort für den initialen Admin-Benutzer (Login-Screen, mind. 8 Zeichen + 1 Sonderzeichen)
- `TRAEFIK_DOMAIN`: öffentliche Domain für HTTPS-Routing via Traefik
- `TRAEFIK_ACME_EMAIL`: E-Mail für Let's Encrypt (ACME)
- `TRAEFIK_DOCKER_API_VERSION`: Docker API-Version für Traefik (Standard `1.41`, hilft bei API-Compat-Fehlern)
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

- `POST /api/auth/login` (Login via Benutzername + Passwort)
- `POST /api/auth/logout`
- `GET /api/me` (Benutzer + Rolle + Berechtigungen)
- `POST /api/clients/register`
- `POST /api/clients/{client_uid}/snapshots`
- `GET /api/clients`
- `DELETE /api/clients/{client_uid}`
- `GET /api/clients/{client_uid}/snapshots`
- `GET /api/clients/{client_uid}/analytics`
- `GET /api/clients/{client_uid}/anomalies`
- `GET /api/clients/{client_uid}/export?format=json|csv|pdf`
- `GET /api/compare?client_uids=A&client_uids=B`
- `GET /api/alerts`
- `GET /api/events` (Admin)
- `GET /api/alert-rules`
- `POST /api/alert-rules` (Admin)
- `PATCH /api/alert-rules/{rule_id}` (Admin)
- `POST /api/onboarding-tokens`
- `GET /api/users` (Berechtigung `manage_users`)
- `POST /api/users` (Berechtigung `manage_users`)
- `PATCH /api/users/{user_id}` (Berechtigung `manage_users`)
- `DELETE /api/users/{user_id}` (Berechtigung `manage_users`)

## Optionale Erweiterungen (umgesetzt)

- Rollenmodell:
  - **admin** über `SERVER_API_KEY`
  - **admin/user** über Login mit `START_ADMIN_USERNAME` + `START_ADMIN_PASSWORD` (bzw. durch Admin angelegte Nutzer)
  - feinere Berechtigungen z. B. `view_dashboard`, `add_clients`, `delete_clients`, `manage_users`
    - `add_clients`/`delete_clients`: nur Gerätebestand (Clients) verwalten
    - `manage_users`: Benutzerkonten anlegen/bearbeiten/löschen
  - Admin-Oberfläche zum Erstellen, Bearbeiten und Löschen von Benutzern im Dashboard
  - Passwortregeln für Benutzer: mindestens 8 Zeichen und mindestens ein Sonderzeichen
  - **agent** über generierte Client-Tokens (nur Datenupload)
- Export:
  - JSON, CSV und PDF je Client (`/api/clients/{uid}/export`)
- Trends und Durchschnittswerte:
  - Analytics-Endpunkt mit Mittelwerten und Trend pro Stunde
- Erkennung von Auffälligkeiten:
  - niedriger freier Speicher
  - hohe CPU-Temperatur
  - Uptime-Reset (möglicher Neustart)
- Protokollierung:
  - Ereignisprotokoll in SQL-Tabelle `event_logs` (Registrierung, Snapshots, Alerts, Auth-Fehler, Token-/Regel-Änderungen)

## Begründete Ergänzungen zu unvollständigen Angaben

- Sensorwerte (Temperatur/Lüfter) und Herstellerinfos können je nach Hardware/Firmware fehlen oder Platzhalter liefern.
- Für Windows werden deshalb mehrere Datenquellen kombiniert:
  - WMIC
  - PowerShell/CIM (`Get-CimInstance`)
- Netzwerkadressen werden über PowerShell-CIM und psutil-Fallback ermittelt, um IPv4/IPv6/MAC robuster zu erfassen.

## Robustheit, Sicherheit, Skalierbarkeit (Prototyp)

- Fehlerbehandlung im Agenten mit Logging + Exponential Backoff
- API-Key-Schutz gegen unbefugten API-Zugriff
- Session-Tokens für Login-Sitzungen im Dashboard
- Zusätzliche pro-Client API-Tokens für Onboarding
- Klare Trennung von Client und Server
- SQL-basierte Persistenz und erweiterbares Datenmodell
- Mehrere Clients können parallel Daten senden

## Hinweis zu Mainboard-/BIOS-Hersteller

Auf Windows nutzt der Client mehrere Wege (WMIC und PowerShell/CIM-Fallback), um Mainboard- und BIOS-Hersteller zu lesen.
Falls ein Hersteller dennoch leer bleibt, liefert die Firmware des Geräts häufig nur Platzhalterwerte.