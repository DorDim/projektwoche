# Anwenderdokumentation - Hardwareueberwachung

Diese Anleitung richtet sich an Admins und Anwender im Tagesbetrieb.
Die Inhalte sind praxisnah als Szenarien aufgebaut.

---

## 1. Schnellstart

1. URL der Anwendung oeffnen (z. B. `https://monitor.example.com`).
2. Mit Benutzername und Passwort anmelden.
3. Im Dashboard einen Client auswaehlen.
4. Werte, Historie, Alerts und Inventardaten pruefen.

Wenn keine Daten sichtbar sind: **Aktualisieren** ausfuehren.

---

## 2. Navigation und Rechte

### Navigation
- **Dashboard**: Client-Liste, Details, Inventarisierung, Analytics, Alerts, Export
- **Vergleich**: Gegenueberstellung mehrerer Clients
- **Nutzer**: Benutzerverwaltung (nur mit entsprechender Berechtigung)

### Rollen-/Rechtekurzinfo

| Recht | Wirkung |
|---|---|
| `view_dashboard` | Dashboard und Vergleich sehen |
| `add_clients` | Onboarding-Token erzeugen, Inventardaten bearbeiten |
| `delete_clients` | Clients loeschen |
| `manage_users` | Benutzer anlegen/aendern/loeschen |
| `manage_alert_rules` | Alert-Regeln pflegen |
| `view_events` | Event-Logs einsehen |

---

## 3. Szenario: Benutzerverwaltung (Admin)

### Ziel
Benutzer mit passenden Rechten einrichten.

### Schritte
1. Als Admin anmelden.
2. Seite **Nutzer** oeffnen.
3. Unter "Neuen Benutzer erstellen" ausfuellen:
   - Benutzername
   - Passwort (mind. 8 Zeichen + Sonderzeichen)
   - Rolle
   - Einzelrechte
4. Speichern und mit Test-Login pruefen.

Hinweis:
- Nicht-Admins koennen keine Admin-Benutzer loeschen/bearbeiten.
- Eigenes Benutzerkonto kann nicht geloescht werden.

---

## 4. Szenario: Neuen Client anbinden

### Voraussetzung
Recht `add_clients`.

### Schritte
1. Dashboard -> **Neuen Client hinzufuegen**.
2. Token erzeugen und kopieren.
3. Installationsbefehl auf Zielgeraet ausfuehren (Windows oder Linux).
4. Zurueck im Dashboard aktualisieren.
5. Client in der Liste pruefen.

---

## 5. Szenario: Inventardaten pflegen

### Ziel
Technische Daten und organisatorische Inventarinformationen verknuepfen.

### Schritte
1. Im Dashboard einen Client waehlen.
2. Im Bereich **Inventarisierung** auf "Inventardaten bearbeiten" klicken.
3. Felder fuellen, z. B.:
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
2. Durchschnittswerte im Zeitraum pruefen.
3. Historie "Freier Speicher", Uptime-Verlauf und Laufwerksauslastung ansehen.
4. Auffaelligkeiten und aktuelle Alerts kontrollieren.
5. Falls noetig Export erstellen (JSON/CSV/PDF).

Praxisbeispiele:
- stark sinkender freier Speicher -> Speicherengpass pruefen
- abrupter Uptime-Abfall -> moeglicher Neustart/Instabilitaet

---

## 7. Szenario: Clients vergleichen

1. Seite **Vergleich** oeffnen.
2. Relevante Clients per Checkbox markieren.
3. Vergleichskarten und Vergleichstabelle auswerten.
4. Auffaellige Systeme im Dashboard detailliert untersuchen.

---

## 8. Exporte nutzen

Pro ausgewaehltem Client verfuegbar:
- **JSON**: vollstaendige strukturierte Daten
- **CSV**: tabellarisch (z. B. fuer Excel)
- **PDF**: kompakter Report inkl. Inventardaten und aktuellem Snapshot

---

## 9. Demo-Daten

- Demo-Clients sind nur fuer den Demo-Benutzer sichtbar.
- Produktive Benutzer sehen keine Demo-Daten.

---

## 10. Fehlerbehebung

### Login funktioniert nicht
- Benutzername/Passwort pruefen
- Konto aktiv?
- Rechte korrekt gesetzt?

### Client erscheint nicht
- Agent auf Zielsystem gestartet?
- API-Token und Server-URL korrekt?
- Dashboard aktualisiert?

### Keine Daten trotz sichtbarem Client
- Netzwerkverbindung pruefen
- Event-Log auf Fehler pruefen
- Server-Logs pruefen

### Datenbankfehler im Compose-Betrieb
- `POSTGRES_PASSWORD` in `.env` pruefen
- bei alten Volumes ggf. altes Passwort oder `docker compose down -v` (Datenverlust)

