# Projektstruktur

```text
frontend/
  src/App.jsx                 Logo, Cookie-Anmeldung, Einstieg
  src/api.js                  API-Client, Fehlertexte, sicherer Vorschaumodus
  src/components/             Übersicht, Rangliste, Grafik, Karte, Gruppen, Admin
  src/previewData.js          Ausschliesslich Beispieldaten
  src/time.js                 Schweizer Startzeiten im Browser
  tests/                     Playwright: Desktop, Mobile, echte lokale API
  logo/                      Vorhandene Logo-Dateien
backend/
  main.py                    API, CORS, Herkunftsschutz, Healthcheck, Scheduler
  database.py                Eine DB-Verbindung, kein produktiver Fallback
  migrations.py              Versionierte additive Schemaänderungen
  models/                    Historische und neue SQLAlchemy-Tabellen
  services/challenge.py       Zentrale, deterministische Wochenwertung
  services/strava.py          OAuth-Tokenrotation, Import, Abgleich, Webhookarbeit
  services/sessions.py        Persistente Website-/Admin-Sitzungen und Gast-Identität
  services/limits.py          Persistente Begrenzung öffentlicher Schreibzugriffe
  routes/                    Dünne HTTP-Schnittstellen
  auth/routes.py             OAuth-Anmeldung und Logout
  tasks/sync_scheduler.py     Periodischer Import ohne blockierten Eventloop
  tests/                     Isolierte API-/Regeltests und lokaler E2E-Server
docs/                        Regeln, API, Bereinigung
Dockerfile                   Render-Build ab Repository-Root
backend/Dockerfile           Alternativer Render-Build ab backend/
docker-compose.yml           Lokale PostgreSQL-/Backend-Umgebung
```

Alle Importwege verwenden denselben Regeldienst. Die Rangliste und die gemeinsame Grafik lesen dieselben `challenge_claims`. Dadurch gibt es keine getrennte Punkteberechnung im Frontend. Öffentliche Antworten enthalten keine Strava-Zugangsdaten oder Browser-Identitäten.

Die alten Tabellen bleiben als Historie erhalten. Neue Challenge-Ergebnisse sind einer Edition zugeordnet; die bisherigen `users.slots` und `total_score` werden nicht für 2026 überschrieben. Neue Datenbankänderungen gehören zusätzlich in `migrations.py`; nur ein Modell zu ändern genügt bei bestehenden Datenbanken nicht.

Render-Aufbau und Einstellungen: [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md). Lokale Start- und Testbefehle: [DEVELOPMENT.md](DEVELOPMENT.md).
