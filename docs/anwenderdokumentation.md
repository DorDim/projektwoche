# Anwenderdokumentation - Hardwareüberwachung

Diese Anleitung richtet sich an Admins und Anwender im Tagesbetrieb.
Die Inhalte sind praxisnah als Szenarien aufgebaut.

---

## 1. Schnellstart

1. URL der Anwendung öffnen (z. B. `https://monitor.example.com`).
2. Mit Benutzername und Passwort anmelden.
3. Im Dashboard einen Client auswählen.
4. Werte, Historie, Alerts und Inventardaten prüfen.

Wenn keine Daten sichtbar sind: **Aktualisieren** ausführen.

---

## 2. Navigation und Rechte

### Navigation
- **Dashboard**: Client-Liste, Details, Inventarisierung, Analytics, Alerts, Export
- **Vergleich**: Gegenüberstellung mehrerer Clients
- **Nutzer**: Benutzerverwaltung (nur mit entsprechender Berechtigung)

### Rollen-/Rechtekurzinfo

| Recht | Wirkung |
|---|---|
| `view_dashboard` | Dashboard und Vergleich sehen |
| `add_clients` | Onboarding-Token erzeugen, Inventardaten bearbeiten |
| `delete_clients` | Clients löschen |
| `manage_users` | Benutzer anlegen/ändern/löschen |
| `manage_alert_rules` | Alert-Regeln pflegen |
| `view_events` | Event-Logs einsehen |

---

## 3. Szenario: Benutzerverwaltung (Admin)

### Ziel
Benutzer mit passenden Rechten einrichten.

### Schritte
1. Als Admin anmelden.
2. Seite **Nutzer** öffnen.
3. Unter "Neuen Benutzer erstellen" ausfüllen:
   - Benutzername
   - Passwort (mind. 8 Zeichen + Sonderzeichen)
   - Rolle
   - Einzelrechte
4. Speichern und mit Test-Login prüfen.

Hinweis:
- Nicht-Admins können keine Admin-Benutzer löschen/bearbeiten.
- Eigenes Benutzerkonto kann nicht gelöscht werden.

---

## 4. Szenario: Neuen Client anbinden

### Voraussetzung
Recht `add_clients`.

### Schritte
1. Dashboard -> **Neuen Client hinzufügen**.
2. Token erzeugen und kopieren.
3. Installationsbefehl auf Zielgerät ausführen (Windows oder Linux).
4. Zurück im Dashboard aktualisieren.
5. Client in der Liste prüfen.

---

## 5. Szenario: Inventardaten pflegen

### Ziel
Technische Daten und organisatorische Inventarinformationen verknüpfen.

### Schritte
1. Im Dashboard einen Client wählen.
2. Im Bereich **Inventarisierung** auf "Inventardaten bearbeiten" klicken.
3. Felder füllen, z. B.:
   - Standort
   - Inventar-Nummer
   - Seriennummer
   - Abteilung / Verantwortliche Person
   - Anschaffungsdatum / Anschaffungspreis
   - Garantie bis / Notizen
4. Speichern.

---

## 6. Szenario: Tagesbetrieb im Dashboard

Empfohlener Ablauf je Client:
1. Zeitraum setzen (1h, 6h, 24h, 7d, 30d, Alles).
2. Durchschnittswerte im Zeitraum prüfen.
3. Historie "Freier Speicher", Uptime-Verlauf und Laufwerksauslastung ansehen.
4. Auffälligkeiten und aktuelle Alerts kontrollieren.
5. Falls nötig Export erstellen (JSON/CSV/PDF).

Praxisbeispiele:
- stark sinkender freier Speicher -> Speicherengpass prüfen
- abrupter Uptime-Abfall -> möglicher Neustart/Instabilität

---

## 7. Szenario: Clients vergleichen

1. Seite **Vergleich** öffnen.
2. Relevante Clients per Checkbox markieren.
3. Vergleichskarten und Vergleichstabelle auswerten.
4. Auffällige Systeme im Dashboard detailliert untersuchen.

---

## 8. Exporte nutzen

- Pro ausgewähltem Client verfügbar:
- **JSON**: vollständige strukturierte Daten
- **CSV**: tabellarisch (z. B. für Excel)
- **PDF**: kompakter Report inkl. Inventardaten und aktuellem Snapshot

---

## 9. Demo-Daten

- Demo-Clients sind nur für den Demo-Benutzer sichtbar.
- Produktive Benutzer sehen keine Demo-Daten.

---

## 10. Fehlerbehebung

### Login funktioniert nicht
- Benutzername/Passwort prüfen
- Konto aktiv?
- Rechte korrekt gesetzt?

### Client erscheint nicht
- Agent auf Zielsystem gestartet?
- API-Token und Server-URL korrekt?
- Dashboard aktualisiert?

### Keine Daten trotz sichtbarem Client
- Netzwerkverbindung prüfen
- Event-Log auf Fehler prüfen
- Server-Logs prüfen

### Datenbankfehler im Compose-Betrieb
- `POSTGRES_PASSWORD` in `.env` prüfen
- bei alten Volumes ggf. altes Passwort oder `docker compose down -v` (Datenverlust)

