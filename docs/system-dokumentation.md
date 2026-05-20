# Systemdokumentation - Hardwareueberwachung

## 1. Zweck und Zielbild

Die Anwendung dient zur zentralen Ueberwachung und Inventarisierung von IT-Endgeraeten.
Client-Agenten liefern in festen Intervallen Hardware- und Betriebsdaten an das Backend.
Die Daten werden in PostgreSQL gespeichert und ueber ein Web-Frontend visualisiert.

Abgedeckte Kernziele:
- konsolidierte Sicht auf alle angebundenen Clients
- rollenbasierter Zugriff auf Monitoring- und Verwaltungsfunktionen
- nachvollziehbare Protokollierung ueber Event-Logs
- exportierbare Daten (JSON, CSV, PDF) fuer Nachweise und Reports

---

## 2. Systemarchitektur

### 2.1 Komponenten

- **Client-Agent (Python)**
  - ermittelt Snapshot-Daten (CPU/RAM/GPU/Disks/Netzwerk/Uptime, Mainboard/BIOS)
  - registriert den Client einmalig
  - sendet Snapshots zyklisch per API

- **Backend (FastAPI + SQLAlchemy)**
  - Authentifizierung und Session-Handling
  - Rechtepruefung pro Endpoint
  - Persistenz in PostgreSQL
  - Analytics, Anomalieerkennung, Export

- **Datenbank (PostgreSQL 18, alpine)**
  - zentrale Persistenz aller fachlichen Daten
  - Datenhaltung fuer Clients, Snapshots, Nutzer, Alerts und Events

- **Reverse Proxy (Traefik v3.7.1)**
  - HTTP->HTTPS-Weiterleitung
  - TLS-Zertifikate via Let's Encrypt
  - Routing auf den FastAPI-Service

- **Frontend (statische Seiten + app.js)**
  - Dashboard (`/`)
  - Vergleich (`/compare`)
  - Nutzerverwaltung (`/users`)

### 2.2 Laufzeit-Datenfluss

1. Benutzer authentifiziert sich per Login (`/api/auth/login`).
2. Session-Token wird als API-Key fuer weitere Requests genutzt.
3. Agent registriert/sendet Snapshot (`/api/clients/register`, `/api/clients/{uid}/snapshots`).
4. Backend speichert Daten, wertet Regeln aus, schreibt Events.
5. Frontend laedt Daten (Clients, Details, Analytics, Alerts, Events) und rendert Visualisierungen.

---

## 3. Sicherheit und Berechtigung

### 3.1 Transport und Netz

- Externe Zugriffe laufen ueber HTTPS (Traefik + ACME).
- Interne Service-Kommunikation laeuft im Compose-Netz.

### 3.2 Authentifizierung

- Login mit Benutzername/Passwort.
- Session-Token werden gehasht gespeichert.
- API-Aufrufe verwenden `X-API-Key`.

### 3.3 Rollen-/Rechtemodell

Rechte:
- `view_dashboard`
- `add_clients`
- `delete_clients`
- `manage_users`
- `manage_alert_rules`
- `view_events`
- `ingest_data` (Agent-/Onboarding-Token)

Feste Sicherheitsregeln:
- Benutzer darf sich nicht selbst loeschen.
- Nicht-Admins duerfen keine Admin-Accounts loeschen/bearbeiten.
- Passwortpolicy: mindestens 8 Zeichen + mindestens ein Sonderzeichen.

---

## 4. Deployment mit Docker Compose

### 4.1 Services

- `traefik` - `traefik:v3.7.1`
- `postgres` - `postgres:18-alpine`
- `server` - Build aus lokalem Dockerfile

### 4.2 PostgreSQL 18+ Besonderheit

Das Setup nutzt das von den offiziellen 18er Images empfohlene Layout:
- `PGDATA=/var/lib/postgresql/18/docker`
- Volume-Mount auf `/var/lib/postgresql`

Dadurch werden Probleme mit altem `/var/lib/postgresql/data`-Layout bei Upgrades vermieden.

### 4.3 Konfiguration

Zentrale `.env`-Variablen:
- `TRAEFIK_DOMAIN`, `TRAEFIK_ACME_EMAIL`
- `SERVER_API_KEY`, `START_ADMIN_USERNAME`, `START_ADMIN_PASSWORD`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`

Hinweis:
- Im Compose-Betrieb baut der Server seine DB-URL automatisch aus `POSTGRES_*`.
- `DATABASE_URL` ist nur fuer externe/nicht-compose Nutzung erforderlich.

### 4.4 Startbefehle

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f traefik
docker compose logs -f postgres
docker compose logs -f server
```

---

## 5. Persistenzmodell (Tabellen)

- `clients` - Stammdaten + Inventarfelder
- `hardware_snapshots` - technische Mess-/Statusdaten je Zeitpunkt
- `alert_rules` - konfigurierbare Regeln
- `alert_events` - ausgeloeste Regeln
- `event_logs` - Audit-/Betriebsereignisse
- `app_users` - Benutzerkonten
- `user_sessions` - aktive Sessions
- `api_tokens` - Onboarding-/Agent-Tokens

---

## 6. API-Ueberblick

### 6.1 Auth
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/me`

### 6.2 Clients und Daten
- `POST /api/clients/register`
- `POST /api/clients/{client_uid}/snapshots`
- `GET /api/clients`
- `PATCH /api/clients/{client_uid}/inventory`
- `DELETE /api/clients/{client_uid}`

### 6.3 Analyse und Export
- `GET /api/clients/{client_uid}/analytics`
- `GET /api/clients/{client_uid}/anomalies`
- `GET /api/clients/{client_uid}/export`
- `GET /api/compare`

### 6.4 Administration
- `POST /api/onboarding-tokens`
- `GET/POST/PATCH/DELETE /api/users`
- `GET /api/events`
- `GET/POST/PATCH /api/alert-rules`

---

## 7. Betrieb und Fehlerbilder

### 7.1 404 ueber Domain
- `TRAEFIK_DOMAIN` pruefen (ohne Protokoll/Pfad)
- Traefik-Logs auswerten

### 7.2 Kein TLS-Zertifikat
- DNS-Ziel und Ports 80/443 pruefen
- ACME-Eintraege in Traefik-Logs pruefen

### 7.3 PostgreSQL Auth-Fehler
- `POSTGRES_PASSWORD` in `.env` pruefen
- bei bestehendem alten Volume ggf. altes Passwort verwenden oder `docker compose down -v` (Datenverlust)

### 7.4 Upgrade auf PostgreSQL 18
- bestehende Alt-Volumes koennen inkompatibel sein
- entweder Backup/Restore durchfuehren oder neues Volume starten

---

## 8. Zugehoerige Modellierungsartefakte

- Use-Case: `docs/uml/anwendungsfalldiagramm.puml`
- Aktivität (Server): `docs/uml/aktivitaetsdiagramm-server.puml`
- Aktivität (Client): `docs/uml/aktivitaetsdiagramm-client.puml`
