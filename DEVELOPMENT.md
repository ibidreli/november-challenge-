# Entwickeln und prüfen

Die Startbefehle stehen in [README.md](README.md). Python 3.11+ und Node.js 22+ verwenden. Auf macOS/Linux entspricht `.venv/Scripts/python.exe` dem Pfad `.venv/bin/python`; Umgebungsvariablen dort mit `export NAME=value` setzen.

## Drei Arbeitsweisen

| Zweck | Start | Daten |
| --- | --- | --- |
| Nur Layout und Bedienung | `cd frontend; npm run dev:ui` | Browser-Beispiele, keine Backend-Anfragen |
| Echtes Frontend/Backend | Uvicorn und `npm run dev` | Lokales SQLite oder ausdrücklich gesetzte lokale PostgreSQL-URL |
| PostgreSQL im Container | `docker compose --env-file .env.local up --build db backend`, daneben `npm run dev` | Eigenes Docker-Volume, PostgreSQL 17 |

Die beiden Startbefehle in eigenen Terminals ausführen. Für lokale Entwicklung eine eigene `.env.local` aus `.env.example` anlegen und mit `--env-file .env.local` ausdrücklich auswählen. Der README-Start setzt zusätzlich eine lokale SQLite-URL. So werden bestehende `.env`-Dateien mit Deployment-Zugangsdaten nicht versehentlich verwendet oder überschrieben. Ein bereits im Terminal gesetzter Wert hat Vorrang vor einer Env-Datei. `LOAD_ENV_FILE=1` aktiviert weiterhin den alten optionalen `.env`-Ladeweg; für die beschriebenen lokalen Starts bleibt es bei `0`. Zugangsdaten und lokale Datenbanken gehören nicht in Git. Der vorhandene lokale `backend/dev.db` wird nicht gelöscht.

## Wo ändere ich etwas?

| Änderung | Datei |
| --- | --- |
| Farben, Abstände, mobile Darstellung | `frontend/src/index.css` |
| Logo, auffällige Anmeldung, angemeldeter Name | `frontend/src/App.jsx` |
| Über uns, OK-Texte und bisherige Ausgaben | `frontend/src/components/About.jsx` |
| Gestaltung der Über-uns-Seite | `frontend/src/components/About.css` |
| Persönliche Übersicht und Wochenhinweis | `frontend/src/components/Dashboard.jsx` |
| Nummerierte Feldchen | `frontend/src/components/ChallengeProgress.jsx` |
| Kompakte Rangliste | `frontend/src/components/Leaderboard.jsx` |
| Gemeinsame Kilometerkurve | `frontend/src/components/ChallengeStats.jsx` |
| Laufgruppen und Formular | `frontend/src/components/Groups.jsx` |
| Interaktive Karte | `frontend/src/components/StartMap.jsx` |
| Admin-Oberfläche | `frontend/src/components/AdminPanel.jsx` |
| Beispieldaten | `frontend/src/previewData.js` |
| Wertung für alle Importwege | `backend/services/challenge.py` |
| Strava-Import und Token-Erneuerung | `backend/services/strava.py` |
| Datenbankänderungen | `backend/models/` und `backend/migrations.py` |

Die Abschlussdistanz und ausgeloste Distanzen werden über `/admin` geändert, ohne Code oder Deployment. `CHALLENGE_YEAR` und `CHALLENGE_MONTH` bestimmen die aktive Edition. Standard ist November (`11`); für einen Oktober-Probelauf auf derselben Website `10` setzen. Die bestehende Datenbank hält Auslosungen und Punkte je Jahr/Monat getrennt; Strava-Verbindungen und Sitzungen bleiben gemeinsam. Ablauf: [OCTOBER_TEST.md](OCTOBER_TEST.md).

## Tests

Vor dem Startdatum der aktiven Edition werden manuelle und automatische Strava-Monatsimporte übersprungen. Dabei werden keine Strava-Anfragen oder Token-Erneuerungen ausgelöst und keine gespeicherten Läufe, Wertungen oder Synchronisationszeitpunkte verändert. Frühere Importfehler werden in der persönlichen Übersicht bis zum Start ausgeblendet. Ab dem ersten Tag nach Schweizer Zeit importiert der Hintergrunddienst automatisch wieder; tatsächliche Fehler werden dann angezeigt. Das gilt für Oktober und November und erfordert keine zusätzliche Render-Einstellung.

API und Wertung, mit automatisch isolierter temporärer SQLite-Datenbank:

```powershell
.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
```

Mit einer **wegwerfbaren** PostgreSQL-Datenbank (der Test leert ihre Anwendungstabellen):

```powershell
docker run --detach --name november-challenge-test-pg --env POSTGRES_PASSWORD=local-test-only --env POSTGRES_DB=challenge_test --publish 127.0.0.1:55432:5432 postgres:17-alpine
$env:TEST_DATABASE_URL="postgresql://postgres:local-test-only@localhost:55432/challenge_test"
.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
Remove-Item Env:TEST_DATABASE_URL
```

Niemals eine produktive URL als `TEST_DATABASE_URL` setzen. Der Name muss zusätzlich `test` enthalten. Nach den Tests den selbst erstellten Testcontainer stoppen/entfernen.

Browsertests mit Desktop- und Handy-Grösse, Kartenbedienung sowie echtem Frontend/Backend:

```powershell
cd frontend
npx playwright install chromium
npm test
npm run build
npm run build:ui
```

`npm test` startet selbst lokale Dienste auf 5178, 5179 und 8021; diese Ports müssen frei sein. Die Python-Umgebung muss wie im README eingerichtet sein. Alternativer Interpreter: Umgebungsvariable `PYTHON`. Die Integration verwendet eine temporäre Datenbank und ausschliesslich lokale Test-Sitzungen. Sie verbindet kein echtes Strava-Konto. Screenshots landen in `output/verification/`, Fehlerdetails in `frontend/test-results/`.

## Kleine Änderungen schnell beurteilen

Mit `dev:ui` entwickeln: Vite aktualisiert die Ansicht automatisch. Bei einer Wertungsänderung die API-Tests ausführen; bei Formularen oder Login zusätzlich `npm test`. Für Auslosungen mit echten lokalen Daten: `/admin` → Challenge → Entwurf speichern → öffentliche Übersicht prüfen → Veröffentlichen. Auslosungen vor dem 1.11. können vorbereitet werden; gewertet wird erst ab dem tatsächlichen Lauftag.

Auslosung korrigieren: `/admin` → Challenge → bei der betroffenen Woche **Auslosung zurücksetzen** → bestätigen. Das funktioniert auch bei bereits begonnenen oder vergangenen Wochen. Die alten Distanzen werden freigegeben und ihre Wertungen entfernt. Gespeicherte Strava-Läufe und manuelle Korrekturen bleiben erhalten; andere Wochen und die Abschlussdistanz bleiben bestehen. Danach neue Distanzen eintragen und **Veröffentlichen**. Die vorhandenen Läufe werden automatisch neu gewertet, ohne erneuten Strava-Import. Das Zurücksetzen betrifft nur die aktuell eingestellte Edition (Jahr/Monat).

## Laufgruppen teilen

Jede Gruppe hat einen kleinen Teilen-Button. Der Dialog zeigt ein schlichtes PNG mit Logo, Distanz, Pace, Datum, Uhrzeit, Ersteller und Treffpunkt-Karte. **Bild teilen** öffnet auf unterstützten Geräten den Teilen-Dialog des Betriebssystems. Andernfalls lädt derselbe Button das Bild herunter.

Das Bild enthält die Adresse `/?tab=groups`; beim nativen Teilen wird dieser Link mitgegeben. Bilder entstehen nur beim Öffnen des Dialogs im Browser. Es gibt keine zusätzliche Backend-Schnittstelle oder Render-Einstellung. Zum Anpassen: `frontend/src/components/ShareRun.jsx`, `frontend/src/shareCard.js` und `frontend/src/runSharing.js`.

Die Karte verwendet Leaflet und OpenStreetMap mit sichtbarer Quellenangabe. Ein anderer Kachelanbieter lässt sich mit `VITE_MAP_TILE_URL` und `VITE_MAP_ATTRIBUTION` vor dem Frontend-Build konfigurieren. Für den Bildexport muss der Anbieter CORS für Kartenkacheln erlauben; andernfalls wird ein Hinweis mit Startkoordinaten exportiert und der Gruppenlink bleibt verfügbar. Für umfangreichere Nutzung die [OSM-Nutzungsbedingungen](https://operations.osmfoundation.org/policies/tiles/) beachten.
