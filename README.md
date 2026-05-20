# Hardwareüberwachung (Prototyp)

Zentrale Hardwareüberwachung mit:
- **FastAPI-Server** (Dashboard + API)
- **Client-Agent** (Hardwaredaten erfassen und senden)
- **PostgreSQL**
- **Traefik + Let's Encrypt** (HTTPS)

Wichtige Funktionen:
- Export pro Client als **CSV, JSON, PDF**
- **Durchschnittswerte je ausgewähltem Zeitraum** pro Client
- Erweiterte **Inventarisierung** pro Gerät (z. B. Standort, Inventar-Nr., Anschaffungsdatum/-preis, Verantwortlicher)
- **Auffälligkeitserkennung** (z. B. Speicher, Uptime-Reset)
- **Ereignis- und Fehlerprotokollierung**
- Frei konfigurierbare **Alarmregeln** mit visueller + akustischer Alarmausgabe

---

## Schnellstart (empfohlen: Docker Compose)

1. Konfiguration kopieren:

```bash
cp .env.example .env
```

2. In `.env` mindestens setzen:

```env
TRAEFIK_DOMAIN=monitor.example.com
TRAEFIK_ACME_EMAIL=admin@example.com
START_ADMIN_USERNAME=admin
START_ADMIN_PASSWORD=MeinSicheresPasswort!
SERVER_API_KEY=change-me
```

3. Stack starten:

```bash
docker compose up -d --build
```

4. Logs prüfen:

```bash
docker compose logs -f traefik
docker compose logs -f server
```

5. Aufrufen:
- Dashboard: `https://DEINE_DOMAIN`
- Vergleich: `https://DEINE_DOMAIN/compare`
- Nutzerverwaltung: `https://DEINE_DOMAIN/users`

> Voraussetzungen für HTTPS:
> - DNS der Domain zeigt auf den Server
> - Ports **80** und **443** sind erreichbar

---

## Login und Rollen

- Login erfolgt über Benutzername + Passwort.
- Initialer Admin kommt aus:
  - `START_ADMIN_USERNAME`
  - `START_ADMIN_PASSWORD`
- Passwortregel: **mindestens 8 Zeichen + mindestens 1 Sonderzeichen**

Wichtige Rechte:
- `add_clients` / `delete_clients` → nur Client-Bestand
- `add_clients` → enthält auch Bearbeitung der Inventardaten
- `manage_users` → Benutzerkonten anlegen/bearbeiten/löschen
- `view_dashboard` → Dashboard/Compare lesen

Demo-Modus (standardmäßig aktiv):
- Benutzer: `DEMO_USERNAME` (Standard `demo`)
- Passwort: `DEMO_PASSWORD` (Standard `Demo!123`)
- Erzeugt automatisch mindestens 5 Demo-Clients mit Verlaufsdaten.

---

## Client installieren

### Windows (Ein-Befehl, empfohlen)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "git clone https://github.com/DorDim/projektwoche.git; cd projektwoche; powershell -ExecutionPolicy Bypass -File .\client\install_windows_background.ps1 -ServerUrl 'https://DEINE_DOMAIN' -ApiKey 'DEIN_TOKEN' -IntervalSeconds 60 -StartNow"
```

### Linux (Ein-Befehl)

```bash
bash -lc 'git clone https://github.com/DorDim/projektwoche.git && cd projektwoche && bash ./client/install_linux_background.sh --server-url "https://DEINE_DOMAIN" --api-key "DEIN_TOKEN" --interval-seconds 60'
```

Hinweis: Das Linux-Skript versucht fehlende venv-Pakete (z. B. `python3-venv`) automatisch zu installieren, falls `ensurepip` fehlt.

---

## Wichtige Umgebungsvariablen

- `TRAEFIK_DOMAIN` – öffentliche Domain
- `TRAEFIK_ACME_EMAIL` – E-Mail für Let's Encrypt
- `TRAEFIK_DOCKER_API_VERSION` – Docker API Override für Traefik (Standard: `1.41`)
- `SERVER_API_KEY` – statischer Admin-API-Key
- `START_ADMIN_USERNAME`, `START_ADMIN_PASSWORD` – initialer Login
- `ENABLE_DEMO_DATA` – Demo-Benutzer und Demo-Clients automatisch erzeugen (Standard `true`)
- `DEMO_USERNAME`, `DEMO_PASSWORD` – Login für Demo-Konto
- `DEMO_CLIENT_COUNT` – Anzahl Demo-Clients (mindestens 5)
- `DEMO_SNAPSHOT_INTERVAL_SECONDS` – Intervall für neue Demo-Snapshots
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` – werden im Compose-Betrieb direkt für DB + Server genutzt
- `DATABASE_URL` – nur für Nicht-Compose/externen Betrieb nötig
- `LOG_DATA_ACCESS_EVENTS` – optionales Logging von reinen Lesezugriffen (Analytics/Anomalien/Export), Standard `false`

---

## Dokumentation und UML

- Anwenderdokumentation (Markdown): `docs/anwenderdokumentation.md`
- Ausführliche Doku: `docs/system-dokumentation.md`
- Use-Case-UML: `docs/uml/anwendungsfalldiagramm.puml`
- Aktivitäts-UML: `docs/uml/aktivitaetsdiagramm.puml`

---

## Troubleshooting (kurz)

- Traefik 404:
  - `TRAEFIK_DOMAIN` exakt prüfen (ohne `https://`, ohne `/`)
  - `docker compose logs -f traefik`
- Kein Zertifikat:
  - DNS + Port 80/443 prüfen
- Linux-Installer bricht bei venv ab:
  - Skript erneut mit Root/Sudo ausführen
- PostgreSQL 18 meldet Fehler zu altem Datenpfad `/var/lib/postgresql/data`:
  - Ursache: bestehendes Volume aus älteren Postgres-Versionen (vor 18)
  - Lösung ohne Datenübernahme: alte DB-Volumes entfernen und Container neu starten  
    `docker compose down -v && docker compose up -d --build`
  - Lösung mit Datenübernahme: zuerst Backup (z. B. `pg_dump`) aus alter Instanz erstellen, danach in neue 18er-Instanz einspielen
- `password authentication failed for user "monitor_user"`:
  - bei bestehendem Daten-Volume gilt weiter das alte DB-Passwort aus der ersten Initialisierung
  - entweder altes Passwort in `.env` setzen oder Volume zurücksetzen (`docker compose down -v`)
