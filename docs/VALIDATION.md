# Lokale Prüfung am 8. Oktober 2026

## Laufgruppen teilen

- **Browser:** alle 13 Browserabläufe erfolgreich, darunter sechs Teilen-Prüfungen auf Desktop und Handy: genau eine Bild-Aktion, PNG-Download, nativer Bildversand mit Benutzeraktivierung und Link zu `?tab=groups`, Abbruch sowie Download bei fehlender Unterstützung oder Kartenfehlern. Der native Teilen-Dialog wird im Test simuliert; es wird keine Nachricht versendet.
- **Integration:** die bisherigen sechs UI-Prüfungen und der Ablauf gegen die echte lokale API bleiben Bestandteil der Suite. Die zuvor ergänzten Gruppen-Direktlinks, die dafür vorgesehene Backend-Schnittstelle und die QR-Code-Abhängigkeit sind entfernt.
- **Build und Sichtprüfung:** Produktionsbuild erfolgreich. Export mit echten OpenStreetMap-Kacheln und sichtbarer Quellenangabe geprüft; PNG und Handy-Dialog unter `output/verification/run-share-real-map.png` und `output/verification/share-mobile-viewport.png`. Keine zusätzliche Render-Konfiguration erforderlich. Tatsächliches Versenden über WhatsApp auf einem echten Handy bleibt als Geräteprüfung offen.

## Oktober direkt auf der bestehenden Website

- **36 Backend-/API-Tests mit PostgreSQL 17:** erfolgreich, einschliesslich Oktober-Importgrenzen in Schweizer Zeit, längstem Tageslauf, automatischem Finale und Rückwechsel zur unveränderten November-Wertung.
- **SQLite:** dieselbe Suite erfolgreich; zwei PostgreSQL-spezifische Tests werden übersprungen.
- **Datenbankmigration:** mit vorhandenen SQLite- und PostgreSQL-Datenbanken geprüft. Auslosungen, Claims, Aktivitäten, alte Punkte, Strava-Tokens und Website-Sitzungen bleiben erhalten. Wiederholte Migration und Monatswechsel sind geprüft.
- **Bestehende Anmeldung:** Oktober und November verwenden dieselben Benutzer und Sitzungen. Auslosungen und Wertungen sind innerhalb derselben Datenbank nach Jahr und Monat getrennt.
- **7 Playwright-Browserabläufe:** erfolgreich, inklusive Desktop, Handy und echter lokaler Frontend-/Backend-Integration.
- **Produktionsbuild:** `npm run build` erfolgreich.
- **Aufräumen:** zusätzlicher Test-Dockerfile, eigener Oktober-E2E-Server, Testkalender-Formular und Strava-Pausenschalter entfernt. Für den Probelauf genügt `CHALLENGE_MONTH=10` auf dem vorhandenen Backend.

Die echte Strava-Verbindung und die Migration der Render-Datenbank wurden lokal nicht ausgeführt. Die Umstellung auf der bestehenden Website beschreibt [OCTOBER_TEST.md](../OCTOBER_TEST.md).

## Vorherige Prüfung am 7. Oktober 2026

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
