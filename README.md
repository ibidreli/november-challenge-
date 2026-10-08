# November Jogging Challenge

Oktober direkt auf der bestehenden Website testen: [OCTOBER_TEST.md](OCTOBER_TEST.md). `CHALLENGE_MONTH=10` aktiviert den Probelauf; `11` stellt November wieder her. Bestehende Datenbank, Domains und Strava-App bleiben gleich.

React/Vite, FastAPI und PostgreSQL. Umsetzung für November 2026 mit Wochen-Auslosungen, automatischer Strava-Wertung, gemeinsamer Kilometerkurve und Läufergruppen mit Karte. Die vorhandenen Logos werden verwendet.

## Schnell anschauen

Voraussetzung: Node.js 22 oder neuer. Im Projektordner:

```powershell
cd frontend
npm ci
npm run dev:ui
```

Öffne `http://localhost:5173`. Die Vorschau enthält Beispieldaten und eine simulierte Anmeldung. Sie ruft keine produktive API auf. Unter `/admin` lässt sich die Verwaltung mit einem beliebigen Passwort anschauen. Die Karte lädt öffentliche OpenStreetMap-Kacheln.

## Frontend und Backend zusammen starten

Python 3.11+ und Node.js 22+. Im Projektordner:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
```

In `.env.local` ein eigenes `ADMIN_PASSWORD` setzen. Strava-Zugangsdaten sind erst für die echte Anmeldung nötig. Die vorhandenen `.env`-Dateien werden dabei nicht überschrieben. Dann Terminal 1 im Projektordner:

```powershell
$env:LOAD_ENV_FILE="0"
$env:DATABASE_URL="sqlite:///backend/dev.db"
.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --env-file .env.local --reload --port 8000
```

Terminal 2:

```powershell
cd frontend
npm ci
npm run dev
```

`http://localhost:5173` → Anwendung, `/admin` → Verwaltung, `http://localhost:8000/docs` → API. Lokal wird ohne `DATABASE_URL` SQLite verwendet; Render benötigt ausdrücklich die bestehende PostgreSQL-Datenbank. Die neue Migration ergänzt Tabellen und Spalten und erhält die bisherigen Resultate.

## Weiterarbeiten

- [Lokale Entwicklung, Tests und typische Änderungen](DEVELOPMENT.md)
- [Render: bestehende Dienste konfigurieren und veröffentlichen](DEPLOYMENT_CHECKLIST.md)
- [Auslosungen und Korrekturen als Admin](ADMIN_PANEL_SETUP.md)
- [Regeln und Datenmodell](docs/CHALLENGE_2026.md)
- [API-Verzeichnis](docs/API.md)
- [Projektstruktur](PROJECT_OVERVIEW.md) und [Bereinigung](docs/CLEANUP.md)
- [Durchgeführte Prüfungen](docs/VALIDATION.md)
- [Ladezeit prüfen und Render optimieren](docs/PERFORMANCE.md)

Der Code ist lokal implementiert. Eine Veröffentlichung, DNS-Änderung oder Änderung der produktiven Render-Datenbank erfolgt nicht durch das lokale Testen.
