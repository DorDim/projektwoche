# Anwenderdokumentation – Hardwareüberwachung

Diese Anleitung ist bewusst praxisnah aufgebaut. Du findest hier typische Szenarien mit klaren Schritten.

## Vorab: Login und Navigation

1. Öffne die Weboberfläche (z. B. `https://deine-domain`).
2. Melde dich mit Benutzername und Passwort an.
3. Nutze die Navigation oben:
   - **Dashboard**
   - **Vergleich**
   - **Anwenderdoku**
   - **Nutzer** (nur mit Berechtigung)

Wichtig:
- Ohne Login sind die Unterseiten nicht zugänglich.
- Sichtbare Bereiche hängen von den Rechten des angemeldeten Nutzers ab.

---

## Szenario 1: Admin startet das System für ein Team

### Ziel
Benutzer anlegen und passende Rechte vergeben.

### Schritte
1. Als Admin anmelden.
2. Seite **Nutzer** öffnen.
3. Unter **Neuen Benutzer erstellen**:
   - Benutzername und Passwort setzen
   - Rolle wählen (User oder Admin)
   - Rechte per Checkbox auswählen
4. Benutzer speichern und Test-Login durchführen.

### Rechte kurz erklärt
- **Dashboard ansehen**: Dashboard + Vergleich nutzen.
- **Clients hinzufügen/löschen**: Geräte aufnehmen oder entfernen.
- **Nutzer verwalten**: Benutzerkonten erstellen/bearbeiten/deaktivieren.
- **Alert-Regeln verwalten**: Grenzwerte konfigurieren.
- **Events ansehen**: Ereignisprotokoll einsehen.

---

## Szenario 2: Neuen Client anbinden (Onboarding)

### Ziel
Einen Rechner als neuen Monitoring-Client registrieren.

### Voraussetzung
Recht **Clients hinzufügen**.

### Schritte
1. Im Dashboard auf **Neuen Client hinzufügen** klicken.
2. Generierten Token kopieren.
3. Auf dem Zielsystem den Ein-Befehl aus dem Dialog ausführen (Windows oder Linux).
4. Im Dashboard auf **Aktualisieren** klicken.
5. Prüfen, ob der neue Client in der Liste erscheint.

---

## Szenario 3: Tägliche Überwachung im Dashboard

### Ziel
Gesundheitszustand eines Clients schnell beurteilen.

### Schritte
1. Im Dashboard einen Client auswählen.
2. **Zeitspanne** setzen (z. B. 1h, 24h, 7d).
3. Bereiche prüfen:
   - **Durchschnittswerte (ausgewählter Zeitraum)**
   - **Historie-Diagramme**
   - **Erkannte Auffälligkeiten**
   - **Aktuelle Alerts**
4. Bei Laufwerken beachten:
   - Gesamtgröße (GB)
   - Freier Speicher in % und GB

Hinweis:
- Durchschnittswerte und Graphen folgen immer der oben gewählten Zeitspanne.

---

## Szenario 4: Mehrere Clients vergleichen

### Ziel
Leistung und Speicherzustand mehrerer Geräte direkt vergleichen.

### Schritte
1. Seite **Vergleich** öffnen.
2. Gewünschte Clients per Checkbox markieren.
3. Vergleichskarten und Diagramm auswerten.
4. Bei Bedarf zurück ins Dashboard wechseln und Details eines einzelnen Clients analysieren.

---

## Szenario 5: Daten für Bericht exportieren

### Ziel
Client-Daten für Nachweise oder Auswertung sichern.

### Schritte
1. Client im Dashboard auswählen.
2. Gewünschtes Format nutzen:
   - **Export JSON**
   - **Export CSV**
   - **Export PDF**
3. Datei lokal speichern und weiterverwenden.

---

## Besondere Hinweise zu Demo-Daten

- Demo-Daten sind **nur** für den Demo-Benutzer sichtbar.
- Andere Benutzer sehen diese Demo-Clients nicht.

---

## Häufige Probleme (Kurzlösung)

### Login funktioniert nicht
- Benutzername/Passwort prüfen
- Groß-/Kleinschreibung prüfen

### Keine Clients sichtbar
- Agent-Installation auf dem Zielsystem prüfen
- Im Dashboard auf **Aktualisieren** klicken
- Prüfen, ob **Dashboard ansehen** aktiviert ist

### Nutzer-Seite fehlt
- Dem Benutzer fehlt vermutlich das Recht **Nutzer verwalten**

