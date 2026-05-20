# Anwenderdokumentation – Hardwareüberwachung

Diese Anleitung richtet sich an Admins und Anwender.  
Sie ist so aufgebaut, dass typische Aufgaben direkt als Schritt-für-Schritt-Ablauf umgesetzt werden können.

---

## Inhaltsverzeichnis

1. [Schnellstart in 5 Minuten](#schnellstart-in-5-minuten)
2. [Grundlagen: Login, Navigation, Rollen](#grundlagen-login-navigation-rollen)
3. [Szenario A: Admin richtet Benutzer ein](#szenario-a-admin-richtet-benutzer-ein)
4. [Szenario B: Neuen Client anbinden](#szenario-b-neuen-client-anbinden)
5. [Szenario C: Tägliche Überwachung im Dashboard](#szenario-c-tägliche-überwachung-im-dashboard)
6. [Szenario D: Clients vergleichen](#szenario-d-clients-vergleichen)
7. [Szenario E: Daten exportieren](#szenario-e-daten-exportieren)
8. [Sichtbarkeit von Demo-Daten](#sichtbarkeit-von-demo-daten)
9. [Checkliste für den Regelbetrieb](#checkliste-für-den-regelbetrieb)
10. [Fehlerbehebung (Troubleshooting)](#fehlerbehebung-troubleshooting)

---

## Schnellstart in 5 Minuten

1. Weboberfläche öffnen (`https://deine-domain`).
2. Mit Benutzername und Passwort anmelden.
3. Im Dashboard einen Client auswählen.
4. Zeitspanne setzen (z. B. 24h).
5. Durchschnittswerte, Alerts und Laufwerkszustand prüfen.

Wenn keine Daten sichtbar sind: zuerst **Aktualisieren** klicken.

---

## Grundlagen: Login, Navigation, Rollen

### Login
- Ohne Login ist kein Zugriff auf Unterseiten möglich.
- Nach dem Login werden nur Menüpunkte angezeigt, für die Berechtigungen vorhanden sind.

### Navigation
- **Dashboard**: Überblick, Details, Alerts, Export
- **Vergleich**: Mehrere Clients nebeneinander auswerten
- **Anwenderdoku**: Kurzanleitung und ausführliche Nutzungshinweise
- **Nutzer**: Benutzerverwaltung (nur mit Berechtigung)

### Rollen und Berechtigungen

| Berechtigung | Bedeutung |
|---|---|
| Dashboard ansehen | Zugriff auf Dashboard und Vergleich |
| Clients hinzufügen | Onboarding neuer Geräte |
| Clients löschen | Entfernen vorhandener Geräte |
| Nutzer verwalten | Benutzer anlegen, bearbeiten, deaktivieren |
| Alert-Regeln verwalten | Grenzwerte konfigurieren |
| Events ansehen | Ereignisprotokoll einsehen |

---

## Szenario A: Admin richtet Benutzer ein

### Ziel
Neue Teammitglieder erhalten nur die Rechte, die sie tatsächlich benötigen.

### Vorgehen
1. Als Admin anmelden.
2. Menü **Nutzer** öffnen.
3. Unter **Neuen Benutzer erstellen**:
   - Benutzername eingeben
   - Passwort vergeben (mind. 8 Zeichen + Sonderzeichen)
   - Rolle wählen (User/Admin)
   - Berechtigungen setzen
4. Benutzer erstellen.
5. Testweise mit dem neuen Benutzer anmelden.

### Empfehlung für den Start
- Für reine Beobachter: nur **Dashboard ansehen**
- Für Technik-Team: zusätzlich **Clients hinzufügen**
- Für Teamleitung/Admin: inkl. **Nutzer verwalten** und ggf. **Alert-Regeln verwalten**

---

## Szenario B: Neuen Client anbinden

### Ziel
Ein neues Gerät liefert automatisch Hardwaredaten an den Server.

### Voraussetzung
Recht **Clients hinzufügen**.

### Schritte
1. Dashboard öffnen.
2. Auf **Neuen Client hinzufügen** klicken.
3. Generierten Token kopieren.
4. Auf dem Zielgerät den angezeigten Ein-Befehl ausführen:
   - Windows (PowerShell)
   - Linux (Bash)
5. Zurück im Dashboard auf **Aktualisieren** klicken.
6. Prüfen, ob der Client in der Liste sichtbar ist.

### Erfolgskriterium
- Client erscheint als Eintrag in der Tabelle.
- Nach kurzer Zeit sind Detaildaten und Verlauf verfügbar.

---

## Szenario C: Tägliche Überwachung im Dashboard

### Ziel
Systemzustand schnell erkennen und bei Problemen reagieren.

### Empfohlener Ablauf
1. Client auswählen.
2. Zeitspanne oben einstellen (1h, 6h, 24h, 7 Tage, 30 Tage, Alles).
3. Nacheinander prüfen:
   - **Durchschnittswerte (ausgewählter Zeitraum)**
   - **Historie-Diagramme**
   - **Erkannte Auffälligkeiten**
   - **Aktuelle Alerts**
4. Laufwerksdetails ansehen:
   - **Gesamt (GB)**
   - **Frei (%)**
   - **Frei (GB)**

### Interpretation
- Stark fallender freier Speicher: mögliche Speicherknappheit.
- Uptime-Reset: Gerät wurde neu gestartet oder war kurz offline.

---

## Szenario D: Clients vergleichen

### Ziel
Mehrere Systeme direkt gegeneinander bewerten.

### Schritte
1. Menü **Vergleich** öffnen.
2. Relevante Clients per Checkbox auswählen.
3. Vergleichskarten und Vergleichsdiagramm prüfen.
4. Auffällige Geräte im Dashboard im Detail untersuchen.

### Typische Fragen
- Welcher Client hat den geringsten freien Speicher?
- Gibt es Ausreißer bei RAM/Threads?
- Haben bestimmte Systeme wiederholt schlechtere Werte?

---

## Szenario E: Daten exportieren

### Ziel
Daten für Berichte, Audits oder externe Auswertung sichern.

### Schritte
1. Im Dashboard einen Client auswählen.
2. Exportformat wählen:
   - **JSON** (strukturierte Rohdaten)
   - **CSV** (Tabellenanalyse, Excel)
   - **PDF** (schnelle Weitergabe)
3. Datei speichern und dokumentieren.

### Hinweis
Für technische Nachvollziehbarkeit ist JSON am vollständigsten.

---

## Sichtbarkeit von Demo-Daten

- Demo-Clients und Demo-bezogene Daten sind nur für den Demo-Benutzer sichtbar.
- Normale Benutzerkonten sehen diese Daten nicht.

Damit bleibt die Produktivsicht sauber getrennt von Demonstrationsdaten.

---

## Checkliste für den Regelbetrieb

- [ ] Täglicher Blick auf Alerts
- [ ] Wöchentliche Prüfung der Top-Risikoclients (Speicher/Uptime)
- [ ] Monatliche Berechtigungsprüfung der Benutzer
- [ ] Regelmäßiger Export für Nachweise oder Reports
- [ ] Prüfen, ob neue Geräte korrekt erfasst werden

---

## Fehlerbehebung (Troubleshooting)

### Problem: Login fehlgeschlagen
**Prüfen:**
- Benutzername korrekt?
- Passwort korrekt?
- Groß-/Kleinschreibung beachtet?
- Benutzerkonto aktiv?

### Problem: Kein Client sichtbar
**Prüfen:**
- Agent auf Zielsystem installiert und gestartet?
- Im Dashboard auf **Aktualisieren** geklickt?
- Berechtigung **Dashboard ansehen** vorhanden?

### Problem: Nutzerverwaltung fehlt
**Prüfen:**
- Berechtigung **Nutzer verwalten** gesetzt?
- Mit dem richtigen Benutzer angemeldet?

### Problem: Keine Daten trotz sichtbarem Client
**Prüfen:**
- Netzwerkverbindung zwischen Client und Server
- API-Token/Server-URL im Agent korrekt
- Logs/Events für Hinweise auf Übertragungsfehler

---

Wenn gewünscht, kann diese Doku zusätzlich als kurze 1-Seiten-Betriebsanleitung (PDF-Format) bereitgestellt werden.

