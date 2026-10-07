# Lokale Prüfung am 7. Oktober 2026

## Ergänzung: Oktober-Probelauf

- **37 Backend-/API-Tests mit PostgreSQL 17:** erfolgreich, einschliesslich Oktober-Importgrenzen in Schweizer Zeit, längstem Tageslauf, verkürzten Testperioden, Wochenwechseln, automatischem Finale und unveränderter November-Wertung.
- **8 Browserabläufe:** erfolgreich, zusätzlich Oktober-Admin mit konfigurierbarem Kalender, Sperre nach Veröffentlichung, persönlichem Fortschritt, Oktober-Diagramm und Handy-/Desktop-Darstellung.
- **Test-Dockerfile mit Oberfläche und API auf einem Host:** gebaut und mit PostgreSQL auf `PORT=10000` gestartet. `/`, `/admin`, Logo-/CSS-/JS-Assets und `/healthz` liefern HTTP 200. Ein 35-km-Testlauf wird als 29 km im Diagramm gewertet; Kalender und Ergebnis bleiben nach Containerwechsel erhalten.
- **Getrennte Datenbanken:** Start im Testmodus gegen eine bestehende produktive Edition wird abgelehnt; umgekehrt ebenso. Migration von einer bereits vorhandenen Wochen-Edition erhält Jahr, Finale und Ergebnisse.
- **Pause für die bestehende Strava-App:** Hintergrundimport, manuelle Synchronisation und Webhook-Worker sind bei `STRAVA_SYNC_ENABLED=0` pausiert. Der Container liefert bei manueller Synchronisation HTTP 409.
- **Fehlerdiagnose:** HTTP-Status und Endpunkt werden protokolliert; Query-Strings, Tokens und Antwortkörper werden nicht geloggt. Fehlgeschlagene Importe erhalten bestehende Punkte.
- **Build und Sichtprüfung:** Produktionsbuild erfolgreich; Oktober-Screenshots auf Handy und Desktop geprüft. Keine horizontale Überbreite in den getesteten Ansichten. `.env` und E2E-Testserver fehlen im Test-Image.

Render-/DNS-Einrichtung und echte Strava-Autorisierung stehen noch aus; Anleitung mit bestehender App: [OCTOBER_TEST.md](../OCTOBER_TEST.md). Die folgenden Punkte dokumentieren die vorherige Prüfung der November-Implementierung.

## Vorherige Prüfung

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
