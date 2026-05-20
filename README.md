# Hardwareüberwachung

Zentrale Hardware- und Inventarüberwachung mit:
- FastAPI-Backend (API + Weboberfläche)
- Python-Client-Agent (Windows/Linux)
- PostgreSQL 18 (alpine)
- Traefik v3.7.1 mit Let's Encrypt

## Funktionsumfang

- Login mit Rollen- und Rechteverwaltung
- Dashboard mit Client-Liste, Detailansicht und Historie
- Erweiterte Inventarisierung je Gerät (Standort, Inventarnummer, Kaufdaten, Notizen)
- Vergleichsseite für mehrere Clients
- Alert-Regeln und Ereignisprotokoll
- Datenexport als JSON, CSV und PDF
- Demo-Benutzer mit Demo-Clients (optional)

---

## Schnellstart (Docker Compose)

1. Konfiguration erstellen:

```bash
cp .env.example .env
```

2. In `.env` mindestens setzen:

```env
TRAEFIK_DOMAIN=monitor.example.com
TRAEFIK_ACME_EMAIL=admin@example.com
START_ADMIN_USERNAME=admin
START_ADMIN_PASSWORD=EinSicheresPasswort!
SERVER_API_KEY=change-me
POSTGRES_PASSWORD=EinSehrSicheresDbPasswort!
```

3. Stack starten:

```bash
docker compose up -d --build
```

4. Verfügbarkeit prüfen:

```bash
docker compose logs -f traefik
docker compose logs -f postgres
docker compose logs -f server
```

5. Seiten aufrufen:
- `https://DEINE_DOMAIN/`
- `https://DEINE_DOMAIN/compare`
- `https://DEINE_DOMAIN/users`

---

## Datenbank-Konfiguration

Im Compose-Betrieb wird die DB-Verbindung automatisch aus `POSTGRES_*` aufgebaut.
Damit ist das Passwort aus `.env` (`POSTGRES_PASSWORD`) für Postgres **und** Server konsistent.

Wichtige Variablen:
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

`DATABASE_URL` wird nur für externe/nicht-compose Setups benötigt.

---

## Rollen und Berechtigungen

- Passwortregel: mindestens 8 Zeichen + mindestens 1 Sonderzeichen
- Rechte:
  - `view_dashboard` - Dashboard/Vergleich ansehen
  - `add_clients` - Onboarding + Inventardaten bearbeiten
  - `delete_clients` - Clients löschen
  - `manage_users` - Benutzer verwalten
  - `manage_alert_rules` - Alert-Regeln verwalten
  - `view_events` - Event-Log einsehen

Zusätzliche Sicherheitsregeln:
- Benutzer kann sich nicht selbst löschen
- Nicht-Admins können keine Admin-Benutzer löschen/bearbeiten

---

## Client-Installation

### Windows (Ein-Befehl)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "git clone https://github.com/DorDim/projektwoche.git; cd projektwoche; powershell -ExecutionPolicy Bypass -File .\client\install_windows_background.ps1 -ServerUrl 'https://DEINE_DOMAIN' -ApiKey 'DEIN_TOKEN' -IntervalSeconds 60 -StartNow"
```

### Linux (Ein-Befehl)

```bash
bash -lc 'git clone https://github.com/DorDim/projektwoche.git && cd projektwoche && bash ./client/install_linux_background.sh --server-url "https://DEINE_DOMAIN" --api-key "DEIN_TOKEN" --interval-seconds 60'
```

---

## Dokumentation

- Anwenderdoku: `docs/anwenderdokumentation.md`
- Systemdoku: `docs/system-dokumentation.md`
- UML Use-Case: `docs/uml/anwendungsfalldiagramm.puml`
- UML Aktivität: `docs/uml/aktivitaetsdiagramm.puml`

---

## Troubleshooting (Kurzfassung)

- **Traefik 404**
  - Domain prüfen (`TRAEFIK_DOMAIN`, ohne Protokoll/Pfad)
  - `docker compose logs -f traefik`

- **TLS-Zertifikat fehlt**
  - DNS auf Server-IP
  - Ports 80/443 erreichbar

- **PostgreSQL 18 Datenpfad-Fehler bei Upgrade**
  - Ursache: altes DB-Volume aus älterer Postgres-Version
  - frischer Start: `docker compose down -v && docker compose up -d --build`
  - mit Datenübernahme: Backup/Restore (z. B. `pg_dump`/`pg_restore`)

- **`password authentication failed`**
  - bei bestehendem Volume gilt das Passwort der ersten Initialisierung
  - entweder ursprüngliches Passwort nutzen oder Volume neu initialisieren (`docker compose down -v`)
