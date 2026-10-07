# Lokale Prüfung am 7. Oktober 2026

- **28 Backend-/API-Tests mit PostgreSQL 17:** erfolgreich, inklusive paralleler Wertungsberechnung und acht gleichzeitiger identischer Gruppen-Teilnahmen ohne Duplikat.
- **SQLite:** dieselbe Suite erfolgreich; der eine PostgreSQL-spezifische Sperrtest wird übersprungen.
- **7 Playwright-Browserabläufe:** erfolgreich auf Desktop (1440 px) und emuliertem Handy (390 px), inklusive Anmeldung, persönlicher Feldchen, aufklappbarer Rangliste, Gruppenformular mit interaktiver Leaflet-Karte und Gast-Teilnahme. Schweizer Uhrzeiten werden unabhängig von der Browser-Zeitzone geprüft.
- **Echte lokale Frontend-/Backend-Integration:** Cookie-Anmeldung nach Neuladen, Entwurf öffentlich verborgen, Veröffentlichung, manuelle Korrektur mit neuer Punktzahl, Gast-Erstellung und Eigentum nach Neuladen, Absage. Keine produktiven Systeme verwendet.
- **Reproduzierbare Installation und Builds:** `npm ci`, `npm run build:ui` und `npm run build` erfolgreich.
- **Docker mit Python 3.11 und PostgreSQL 17:** Build und Start auf Render-ähnlichem `PORT=10000` erfolgreich; Healthcheck meldet `ok`.
- **Migration einer vorhandenen PostgreSQL-Struktur:** alte 465 Punkte, 30 gewertete Aktivitäts-km und 30-km-Claim bleiben erhalten; alte VARCHAR-Strava-ID wird BIGINT. Nach Neustart bleiben Admin-Sitzung und Gast-Eigentum gültig.
- **Docker-Ausschlüsse:** `.env` und lokaler E2E-Testserver sind im endgültigen Image nicht enthalten.
- **Karte:** Leaflet-Bedienung in Browsertests mit deterministischen Testkacheln; zusätzlich echter OpenStreetMap-Kachelabruf mit HTTP 200 geprüft.
- **Visuelle Prüfung:** Screenshots von Übersicht, Rangliste, Gruppen und Formular auf Desktop/Handy unter `output/verification/`. Keine horizontale Überbreite in den getesteten Handyansichten.

Strava-Netzwerkzugriffe sind in API-Tests gemockt und unbekannte Netzwerkzugriffe gesperrt. Echte Strava-Autorisierung, produktive DNS-/Cookie-Konfiguration und die Migration der Render-Datenbank müssen nach den Kontoeinstellungen aus [DEPLOYMENT_CHECKLIST.md](../DEPLOYMENT_CHECKLIST.md) auf der Zielumgebung geprüft werden. Es wurde nichts zu Render hochgeladen oder produktiv geändert.
