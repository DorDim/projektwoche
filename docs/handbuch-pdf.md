<!-- handbuch-pdf.md -->

# Handbuch  
## Zentrale Hardwareüberwachung

**Kunden- und Supportdokumentation**

---

**Projekt:** Hardwareüberwachung  
**Version:** 1.0  
**Stand:** 21.05.2026  
**Gültig für:** Produktiv- und Supportbetrieb  
**Erstellt von:** Projektteam  

---

**Hinweis:**  
Dieses Dokument wurde für den PDF-Export strukturiert aufgebaut.  
Seitenumbrüche sind explizit gesetzt.

<div style="page-break-after: always;"></div>

# Dokumentinformationen

## Ziel des Dokuments
Dieses Handbuch beschreibt die Nutzung und den Betrieb der Software aus Sicht von:
- Anwendern
- Administratoren
- Support

## Zielgruppen
- **Kunden/Anwender:** tägliche Arbeit mit Dashboard, Vergleich und Export  
- **Administratoren:** Benutzerverwaltung, Berechtigungen, Alert-Regeln, Onboarding  
- **Support:** Fehleranalyse, Wiederherstellung, strukturierte Bearbeitung von Incidents

## Geltungsbereich
Das Handbuch gilt für das aktuell ausgerollte Setup mit:
- FastAPI-Server
- PostgreSQL (18-alpine)
- Traefik (v3.7.1)
- Windows- und Linux-Client-Agenten

<div style="page-break-after: always;"></div>

# Inhaltsverzeichnis

1. [Systemüberblick](#1-systemüberblick)  
2. [Schnellstart](#2-schnellstart)  
3. [Rollen und Berechtigungen](#3-rollen-und-berechtigungen)  
4. [Bedienung der Weboberfläche](#4-bedienung-der-weboberfläche)  
5. [Client-Onboarding](#5-client-onboarding)  
6. [Inventarisierung](#6-inventarisierung)  
7. [Alerts und Events](#7-alerts-und-events)  
8. [Exportfunktionen](#8-exportfunktionen)  
9. [Support-Playbook](#9-support-playbook)  
10. [Troubleshooting](#10-troubleshooting)  
11. [Sicherheit](#11-sicherheit)  
12. [FAQ](#12-faq)  

<div style="page-break-after: always;"></div>

# 1) Systemüberblick

Die Software dient der zentralen Überwachung und Inventarisierung von Endgeräten.

## Kernkomponenten
- **Traefik:** TLS/HTTPS, Routing, Zertifikate
- **FastAPI:** API und Webanwendung
- **PostgreSQL:** persistente Speicherung
- **Client-Agent:** Registriert Geräte und sendet Snapshots

## Kernfunktionen
- Login und rollenbasierte Zugriffskontrolle
- Dashboard mit Clientdetails und Historie
- Vergleichsansicht mehrerer Clients
- Inventarverwaltung pro Gerät
- Alert-Regeln und Event-Log
- Exporte als JSON, CSV und PDF

---

# 2) Schnellstart

1. `.env` aus `.env.example` erstellen  
2. Domain, Admin-Zugang und DB-Parameter setzen  
3. Stack starten:
   ```bash
   docker compose up -d --build
   ```
4. Anwendung über `https://<deine-domain>` aufrufen  
5. Mit Start-Admin anmelden

<div style="page-break-after: always;"></div>

# 3) Rollen und Berechtigungen

| Recht | Bedeutung |
|---|---|
| `view_dashboard` | Dashboard und Vergleich lesen |
| `add_clients` | Onboarding-Token erstellen, Inventardaten bearbeiten |
| `delete_clients` | Clients löschen |
| `manage_users` | Benutzer anlegen, ändern, löschen |
| `manage_alert_rules` | Alert-Regeln erstellen/ändern |
| `view_events` | Event-Protokoll anzeigen |

## Sicherheitsregeln in der Benutzerverwaltung
- Ein Benutzer kann sich **nicht selbst löschen**
- Ein Benutzer kann sich **nicht selbst deaktivieren**
- Nicht-Admins dürfen keine Admin-Benutzer löschen/bearbeiten

---

# 4) Bedienung der Weboberfläche

## Dashboard (`/`)
- Clientliste mit Status
- Detailansicht mit Hardwareinformationen
- Zeitbereichsfilter für Historie
- Inventardaten (über Modal)
- Alert- und Exportfunktionen

## Compare (`/compare`)
- Vergleich mehrerer Clients
- Erkennen von Ausreißern und Abweichungen

## Users (`/users`)
- Benutzer- und Rechteverwaltung
- Aktiv/Deaktiv-Status
- Schutzregeln für kritische Aktionen

## Schritt-für-Schritt: Typische Bedienaufgaben (Anwender)

### A) Im Dashboard einen Client auswählen und Details prüfen
1. In der oberen Navigation auf **Dashboard** klicken.
2. In der Client-Tabelle auf den gewünschten Client (Hostname/UID) klicken.
3. Rechts/unterhalb im Detailbereich prüfen:
   - Letzter Snapshot
   - Laufwerke (frei/gesamt)
   - Uptime
   - Hardwaredetails
4. Bei Bedarf oben den Zeitraum wechseln (z. B. 24h oder 7 Tage), damit Diagramme und Durchschnittswerte passend gefiltert werden.

### B) Vergleich von mehreren Clients aufrufen
1. In der Navigation auf **Compare** klicken.
2. In der Liste die gewünschten Clients per Checkbox markieren.
3. Vergleichswerte und Unterschiede prüfen.
4. Bei Auffälligkeiten zurück ins **Dashboard** wechseln und betroffenen Client im Detail öffnen.

### C) Inventardaten für ein Gerät pflegen
1. **Dashboard** öffnen und Client auswählen.
2. Auf **Inventardaten bearbeiten** (Modal öffnen) klicken.
3. Felder ausfüllen (z. B. Standort, Inventarnummer, Verantwortliche Person).
4. Auf **Speichern** klicken.
5. Prüfen, ob die neuen Daten direkt in der Detailansicht sichtbar sind.

### D) Export für einen Client erzeugen
1. **Dashboard** öffnen und Client auswählen.
2. Gewünschtes Exportformat anklicken:
   - **JSON**
   - **CSV**
   - **PDF**
3. Datei lokal speichern.
4. Für Supportfälle Dateiname und Exportzeitpunkt im Ticket dokumentieren.

### E) Onboarding eines neuen Clients (mit Berechtigung)
1. **Dashboard** öffnen.
2. Auf **Neuen Client hinzufügen** klicken.
3. Token generieren und den angezeigten Installationsbefehl kopieren.
4. Befehl auf Zielsystem ausführen (Windows/Linux).
5. Zurück im Dashboard auf **Aktualisieren** klicken.
6. Prüfen, ob der neue Client in der Tabelle erscheint.

<div style="page-break-after: always;"></div>

# 5) Client-Onboarding

## Ablauf
1. Im Dashboard „Neuen Client hinzufügen“ öffnen  
2. Onboarding-Token generieren  
3. Installationsbefehl auf Zielsystem ausführen  
4. Registrierung prüfen  
5. Erste Snapshot-Daten prüfen

## Plattformen
- **Windows:** PowerShell-Installer, Scheduled Task
- **Linux:** Bash-Installer, systemd-user Service (Fallback: nohup)

---

# 6) Inventarisierung

Pro Client können folgende Daten gepflegt werden:
- Standort
- Inventarnummer
- Seriennummer
- Abteilung
- Verantwortliche Person
- Lieferant
- Anschaffungsdatum
- Anschaffungspreis
- Garantie bis
- Notizen

Bearbeitung erfolgt über ein Modal in der Detailansicht.

---

# 7) Alerts und Events

## Alerts
- Alert-Regeln werden serverseitig gegen Snapshot-Werte geprüft
- Bei Regelverletzung wird ein Alert erzeugt

## Events
- Relevante Aktionen und Systemereignisse werden protokolliert
- Zugriff auf Events nur mit `view_events`

<div style="page-break-after: always;"></div>

# 8) Exportfunktionen

Verfügbare Formate:
- **JSON:** strukturierte Rohdaten
- **CSV:** tabellarische Auswertung
- **PDF:** Berichtsdokument mit Inventar + letztem Snapshot

---

# 9) Support-Playbook

## Standardablauf bei Störungen
1. Ticketdaten erfassen (wer, wann, was, wo)  
2. Infrastrukturstatus prüfen (`traefik`, `server`, `postgres`)  
3. Berechtigungen des betroffenen Benutzers prüfen  
4. Clientzustand und letzte Snapshots prüfen  
5. Ursache eingrenzen  
6. Maßnahme umsetzen und dokumentieren  

## Dokumentationspflicht
- Ursache
- Maßnahme
- Ergebnis
- ggf. Prävention

## Support-Leitfaden: Anwender telefonisch/remote durch die UI führen

### Leitfaden 1: „Ich sehe meinen Client nicht“
1. Anwender auf **Dashboard** navigieren lassen.
2. Anwender auf **Aktualisieren** hinweisen.
3. Prüfen lassen, ob Such-/Filtereingaben gesetzt sind.
4. Falls weiterhin unsichtbar:
   - Onboarding-Schritt erneut starten
   - Agent-Status auf Zielgerät prüfen
   - Event-Log/Server-Logs gegenprüfen

### Leitfaden 2: „Ich kann keine Events sehen“
1. Anwender auf **Dashboard** führen.
2. Prüfen, ob Event-Bereich fehlt oder leer ist.
3. In **Users** die Benutzerrechte kontrollieren:
   - `view_events` gesetzt?
4. Nach Rechteänderung neu anmelden lassen.

### Leitfaden 3: „Export funktioniert nicht“
1. Anwender einen konkreten Client im Dashboard auswählen lassen.
2. Exportformat erneut anklicken.
3. Browser-Downloadblocker prüfen.
4. Bei Fehlertext:
   - Meldung wörtlich ins Ticket übernehmen
   - Server-Logs prüfen
   - bei Bedarf Testexport mit Adminkonto durchführen

### Leitfaden 4: „Benutzer kann nicht deaktiviert werden“
1. In **Users** prüfen, ob der betroffene Benutzer der aktuell angemeldete ist.
2. Hinweis geben: Selbst-Deaktivierung ist absichtlich blockiert.
3. Lösung:
   - Mit anderem berechtigten Konto anmelden und gewünschten Benutzerstatus ändern.

---

# 10) Troubleshooting

## Traefik zeigt 404
- `TRAEFIK_DOMAIN` prüfen (ohne `https://`, ohne Pfad)
- Traefik-Logs:
  ```bash
  docker compose logs -f traefik
  ```

## Login funktioniert nicht
- Benutzername/Passwort korrekt?
- Benutzer aktiv?
- Rechte korrekt zugewiesen?

## Keine Daten vom Client
- Agent aktiv?
- Token/Server-URL korrekt?
- Netzwerk erreichbar?

## DB-Authentifizierung fehlgeschlagen
- `POSTGRES_PASSWORD` prüfen
- Bei altem Volume ggf. historisches Passwort beachten

<div style="page-break-after: always;"></div>

# 11) Sicherheit

- HTTPS/TLS im externen Zugriff
- Passwortpolicy (min. 8 Zeichen + Sonderzeichen)
- Token-Hashing serverseitig
- Rollenbasierte Zugriffskontrolle
- Schutz kritischer Benutzeraktionen

---

# 12) FAQ

**Warum sehe ich keine Events?**  
Es fehlt wahrscheinlich das Recht `view_events`.

**Warum kann ich mich nicht selbst deaktivieren?**  
Das ist eine Sicherheitsmaßnahme gegen versehentlichen Kontoverlust.

**Warum sind Demo-Daten nicht überall sichtbar?**  
Demo-Daten sind bewusst vom Produktivkontext getrennt.

---

## Abschluss

Hierbei handelt es sich um ein Tool, das im Rahmen einer Projektarbeit entstanden ist.
