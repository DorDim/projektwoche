# Systemdokumentation – Hardwareüberwachung

## 1. Ziel

Das System erfasst Hardware- und Betriebsdaten von Clients zentral, speichert sie in einer SQL-Datenbank und stellt sie im Web-Dashboard inkl. Historie, Vergleich, Alarmierung und Export bereit.

---

## 2. Architektur

## 2.1 Komponenten

- **Client-Agent (Python)**
  - sammelt Hardwaredaten
  - registriert sich am Server
  - sendet Snapshots zyklisch
- **API/Backend (FastAPI + SQLAlchemy)**
  - Authentifizierung + Rollen/Rechte
  - Speicherung und Auswertung
  - Export (JSON/CSV/PDF)
- **Datenbank (PostgreSQL)**
- **Reverse Proxy (Traefik)**
  - HTTPS-Terminierung
  - Let's Encrypt Zertifikate
- **Frontend (Tailwind + Chart.js)**
  - Dashboard (`/`)
  - Vergleich (`/compare`)
  - Nutzerverwaltung (`/users`)

## 2.2 Datenfluss

1. Benutzer meldet sich im Login-Screen an.
2. Backend erstellt Session-Token.
3. Client-Agent sendet Daten an API-Endpunkte.
4. Backend speichert Snapshots, bewertet Regeln, erzeugt ggf. Alerts.
5. Dashboard lädt Daten, Trends, Anomalien und Vergleiche.

---

## 3. Sicherheit

## 3.1 Transport

- Extern: HTTPS via Traefik + Let's Encrypt
- Intern (Compose-Netz): HTTP zwischen Traefik und Server

## 3.2 Authentifizierung

- Login: Benutzername + Passwort (`POST /api/auth/login`)
- Session-Token über `X-API-Key`
- Logout: `POST /api/auth/logout`

## 3.3 Rollen und Berechtigungen

Zentrale Berechtigungen:
- `view_dashboard`
- `add_clients`
- `delete_clients`
- `manage_users`
- `manage_alert_rules`
- `view_events`
- `ingest_data` (Agent-Token)

Regeln:
- Benutzer darf sich nicht selbst löschen.
- Nicht-Admins dürfen keine Admin-Benutzer bearbeiten/löschen.
- Passwortregeln: mindestens 8 Zeichen + mindestens ein Sonderzeichen.

---

## 4. Deployment (Docker Compose)

## 4.1 Relevante Services

- `traefik` (v3.7.1)
- `server` (FastAPI)
- `postgres` (18-alpine)

## 4.2 Relevante `.env` Variablen

- `TRAEFIK_DOMAIN`
- `TRAEFIK_ACME_EMAIL`
- `TRAEFIK_DOCKER_API_VERSION`
- `SERVER_API_KEY`
- `START_ADMIN_USERNAME`
- `START_ADMIN_PASSWORD`
- `DATABASE_URL`

## 4.3 Start

```bash
cp .env.example .env
docker compose up -d --build
```

---

## 5. Datenmodell (wichtigste Tabellen)

- `clients`
- `hardware_snapshots`
- `alert_rules`
- `alert_events`
- `api_tokens` (Onboarding/Agent-Tokens)
- `app_users`
- `user_sessions`
- `event_logs`

---

## 6. Haupt-Endpunkte

Authentifizierung:
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/me`

Clients:
- `POST /api/clients/register`
- `POST /api/clients/{client_uid}/snapshots`
- `GET /api/clients`
- `DELETE /api/clients/{client_uid}`

Analyse/Export:
- `GET /api/clients/{client_uid}/analytics`
- `GET /api/clients/{client_uid}/anomalies`
- `GET /api/clients/{client_uid}/export`
- `GET /api/compare`

Verwaltung:
- `POST /api/onboarding-tokens`
- `GET/POST/PATCH/DELETE /api/users`
- `GET /api/events`
- `GET/POST/PATCH /api/alert-rules`

---

## 7. Betrieb und Troubleshooting

## 7.1 Traefik liefert 404

- `TRAEFIK_DOMAIN` exakt prüfen (kein `https://`, kein Pfad)
- Traefik-Logs prüfen:
  ```bash
  docker compose logs -f traefik
  ```

## 7.2 Kein Zertifikat

- DNS zeigt auf Server?
- Port 80/443 offen?
- ACME-Logs in Traefik prüfen

## 7.3 Linux-Agent: `ensurepip is not available`

- Installer erneut mit Root/Sudo ausführen
- Script versucht automatisch venv-Pakete zu installieren

---

## 8. UML

- Use-Case: `docs/uml/anwendungsfalldiagramm.puml`
- Aktivität: `docs/uml/aktivitaetsdiagramm.puml`
