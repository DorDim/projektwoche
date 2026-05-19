# Anwenderdokumentation – Hardwareüberwachung

Diese Anleitung erklärt die tägliche Nutzung der Oberfläche in einfachen Schritten.

## 1) Anmelden

1. Öffne die Weboberfläche (z. B. `https://deine-domain`).
2. Gib Benutzername und Passwort ein.
3. Klicke auf **Anmelden**.

Hinweis:
- Ohne Login ist kein Zugriff auf Dashboard, Vergleich oder Nutzerverwaltung möglich.
- Welche Bereiche sichtbar sind, hängt von deinen Rechten ab.

## 2) Dashboard verstehen

Im Dashboard siehst du:
- **Client-Liste** mit Online-/Offline-Status
- **Client-Details** mit Hardwaredaten
- **Durchschnittswerte** für den oben gewählten Zeitraum
- **Alerts** und (bei Berechtigung) Ereignisprotokoll

### Zeitraum wählen

Über **Zeitspanne** steuerst du, welche Daten für Graphen und Durchschnittswerte genutzt werden.

## 3) Clients hinzufügen (Onboarding)

Wenn du das Recht **Clients hinzufügen** hast:

1. Klicke auf **Neuen Client hinzufügen**.
2. Kopiere den generierten Token.
3. Nutze den angezeigten Ein-Befehl für Windows oder Linux.
4. Aktualisiere das Dashboard – der neue Client sollte erscheinen.

## 4) Vergleichsseite nutzen

Unter **Vergleich**:

1. Mehrere Clients per Checkbox auswählen.
2. Vergleichstabelle und Diagramm zeigen die wichtigsten Kennzahlen nebeneinander.

## 5) Daten exportieren

Beim ausgewählten Client im Dashboard:
- **Export JSON**
- **Export CSV**
- **Export PDF**

So kannst du Daten für Reports oder externe Auswertung sichern.

## 6) Nutzerverwaltung (nur mit Berechtigung)

Unter **Nutzer** kannst du:
- Benutzer anlegen
- Rechte vergeben
- Benutzer bearbeiten/deaktivieren

Wichtige Unterschiede:
- **Clients hinzufügen/löschen**: betrifft nur Geräte.
- **Nutzer verwalten**: betrifft Benutzerkonten und Rollen.

## 7) Rechte und Demo-Daten

- Demo-Daten sind nur für den Demo-Benutzer sichtbar.
- Andere Benutzer sehen diese Demo-Clients nicht.

## 8) Häufige Probleme

### Login funktioniert nicht
- Benutzername/Passwort prüfen
- Auf Groß-/Kleinschreibung achten

### Keine Clients sichtbar
- Prüfen, ob Agenten korrekt installiert sind
- Auf **Aktualisieren** klicken
- Berechtigung **Dashboard ansehen** prüfen

### Keine Nutzerverwaltung sichtbar
- Es fehlt vermutlich die Berechtigung **Nutzer verwalten**.

