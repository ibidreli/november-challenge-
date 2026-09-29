# November Challenge - Projektuebersicht

## 1. Zweck der Anwendung

Die Anwendung verwaltet eine monatliche Jogging-Challenge. Nutzer verbinden ihr Strava-Konto, ihre Laufaktivitaeten werden importiert und einer Kilometer-Slot-Liste zugeordnet. Das Dashboard zeigt Nutzer, belegte Slots und Punktestand. Ein geschuetztes Admin-Panel erlaubt die Verwaltung von Spielern und manuellen Aktivitaeten.

## 2. Gesamtarchitektur

```text
Browser
  |
  +--> React/Vite Frontend
  |      +--> Dashboard
  |      +--> Strava Login / OAuth Callback
  |      +--> Admin Panel (/admin)
  |
  +--> FastAPI Backend
         +--> Auth- und OAuth-Routen
         +--> User- und Activity-Routen
         +--> Admin-Routen
         +--> Strava Webhook
         +--> Background-Scheduler
                |
                +--> Strava API
         |
         +--> SQLAlchemy
                |
                +--> PostgreSQL in Produktion
                +--> SQLite-Fallback lokal
```

## 3. Ablauf eines normalen Nutzerbesuchs

1. `frontend/src/main.jsx` setzt die API-Basis-URL und liest optional ein `access_token` aus URL oder Session Storage.
2. `frontend/src/App.jsx` entscheidet anhand von URL oder Hash zwischen Dashboard und Admin-Panel.
3. Das Dashboard lädt Nutzer- und Aktivitaetsdaten ueber Axios vom Backend.
4. Das Backend prueft den Bearer-Token oder das Cookie in `backend/routes/users.py`.
5. SQLAlchemy liest den Nutzer sowie `slots` und `total_score` aus der Datenbank.
6. Das Frontend stellt Rangliste, Kilometer und Slots dar.

Beim normalen Reload wird kein Strava-Sync durch das Frontend ausgeloest. Der automatische Sync laeuft serverseitig.

## 4. Strava-OAuth und Aktivitaetsverarbeitung

### Anmeldung

1. `GET /auth/login` baut die Strava-Autorisierungs-URL.
2. Strava leitet zu `GET /auth/callback` zurueck.
3. Das Backend tauscht den Code gegen Access- und Refresh-Token aus und speichert den Nutzer.
4. Das Frontend erhaelt beziehungsweise verwendet den Zugangstoken fuer weitere Requests.

### Import einer Aktivitaet

Aktivitaeten kommen auf zwei Wegen ins System:

- `backend/routes/strava_webhook.py` verarbeitet neue Strava-Events sofort oder versucht sie im Hintergrund erneut.
- `backend/tasks/sync_scheduler.py` prueft alle 30 Sekunden, ob fuer einen Nutzer ein 30-Minuten-Sync faellig ist, und startet den internen Strava-Sync.

Die Verarbeitung in `backend/routes/activities.py`:

1. Es werden nur Laufarten wie Run, Trail Run und Virtual Run akzeptiert.
2. Datum und Distanz werden aus der Strava-Aktivitaet gelesen.
3. Aktivitaeten ausserhalb des Challenge-Monats werden ignoriert.
4. Pro Nutzer und Tag wird nur ein Claim angelegt.
5. Die Distanz wird abgerundet und dem hoechsten noch freien Kilometer-Slot zugewiesen.
6. `User.slots`, `User.total_score` und der zugehoerige `Claim` werden gespeichert.

Manuelle Aktivitaeten haben Vorrang: `sync_recent_activities_from_strava()` ueberspringt eine Strava-Aktivitaet, wenn fuer denselben Nutzer und Tag bereits `is_manual=True` existiert.

## 5. Admin-Ablauf

1. `/admin` wird in `App.jsx` erkannt und rendert `AdminPanel`.
2. `POST /admin/login` prueft `ADMIN_PASSWORD` und gibt einen zeitlich begrenzten Admin-Token zurueck.
3. Das Frontend speichert diesen Token in `localStorage` und sendet ihn als `X-Admin-Token`.
4. `backend/routes/admin.py` stellt Spieler- und Aktivitaetsverwaltung bereit.
5. Manuelle Aktivitaeten werden mit `is_manual=True` gespeichert.
6. Beim Loeschen oder Zuruecksetzen werden Aktivitaeten, Claims, Slots und Punktestand angepasst.

Wichtige Admin-Routen:

| Zweck | Route |
| --- | --- |
| Login/Logout | `POST /admin/login`, `POST /admin/logout` |
| Spieler | `GET/POST /admin/users`, `PUT/DELETE /admin/users/{user_id}` |
| Aktivitaeten | `GET/POST /admin/users/{user_id}/activities` |
| Aktivitaet loeschen | `DELETE /admin/users/{user_id}/activities/{activity_id}` |
| Slots zuruecksetzen | `POST /admin/users/{user_id}/reset-slots` |

## 6. Zentrale Dateien

| Datei | Verantwortung |
| --- | --- |
| `backend/main.py` | FastAPI-App, CORS, Router, Startup, Scheduler, Fallback-Endpunkte |
| `backend/database.py` | Datenbank-URL, Engine, Sessions und Migrationen |
| `backend/models/user.py` | Nutzer, 30 Slots, Score und Slot-Zuweisung |
| `backend/models/activity.py` | Strava- und manuelle Aktivitaeten |
| `backend/models/claim.py` | Zuordnung einer Aktivitaet zu einem Kilometer-Slot |
| `backend/auth/routes.py` | Strava-OAuth, Token und periodischer Aktivitaetsimport |
| `backend/routes/activities.py` | Challenge-Regeln, Slot-Auswahl und Activity Processing |
| `backend/routes/users.py` | Nutzerprofil, Nutzerliste und manueller Sync-Trigger |
| `backend/routes/strava_webhook.py` | Strava-Webhooks und Retry-Verarbeitung |
| `backend/routes/admin.py` | Geschuetzte Admin-API |
| `backend/tasks/sync_scheduler.py` | Automatischer Sync alle 30 Minuten |
| `frontend/src/main.jsx` | React-Start, Axios und Token-Konfiguration |
| `frontend/src/App.jsx` | Seitenumschaltung Dashboard/Admin |
| `frontend/src/components/Dashboard.jsx` | Oeffentliche Challenge-Ansicht |
| `frontend/src/components/AdminPanel.jsx` | Admin-Oberflaeche |
| `frontend/vite.config.js` | Vite-Server und Entwicklungs-Proxy |
| `frontend/public/_redirects` | SPA-Fallback fuer Hosting |
| `docker-compose.yml` | Lokale beziehungsweise containerisierte Services |
| `deploy/nginx.conf` | Reverse-Proxy-Konfiguration |

## 7. Wichtige Konfiguration

| Variable | Verwendung |
| --- | --- |
| `DATABASE_URL` | PostgreSQL-Verbindung; lokal ist SQLite als Fallback moeglich |
| `STRAVA_CLIENT_ID` | Strava OAuth Client-ID |
| `STRAVA_CLIENT_SECRET` | Strava OAuth Secret |
| `STRAVA_REDIRECT_URI` | Registrierte OAuth-Callback-URL |
| `STRAVA_SCOPE` | Strava-Berechtigungen |
| `CHALLENGE_MONTH` | Challenge-Monat, standardmaessig November |
| `ADMIN_PASSWORD` | Passwort fuer das Admin-Panel |
| `FRONTEND_URL` | Erlaubte Frontend-Origin fuer CORS |
| `CUSTOM_DOMAIN` | Zusaetzliche erlaubte Domain fuer CORS |
| `REQUIRE_POSTGRES` | Erzwingt PostgreSQL statt SQLite |
| `LOAD_ENV_FILE` | Aktiviert lokales Laden der `.env`-Datei |

## 8. Startpunkte und Diagnose

- Backend-Einstieg: `backend/main.py`
- Frontend-Einstieg: `frontend/src/main.jsx`
- Healthcheck: `GET /healthz`
- API-Grundroute: `GET /`
- DB-Fehlerdiagnose bei fehlgeschlagenem Startup: `GET /debug/nodb`
- DB-Status und Zaehler: `GET /debug/db_info`
- Produktions- und Domain-Schritte: `DEPLOYMENT_CHECKLIST.md`
- Admin-Einrichtung: `ADMIN_PANEL_SETUP.md`

## 9. Bekannte Punkte beim Weiterentwickeln

- `backend/main.py` startet bei Datenbank- oder Routerfehlern bewusst mit eingeschraenkten Fallback-Routen. Deshalb muss bei einem 503 zuerst `/debug/nodb` und der Backend-Log geprueft werden.
- Die automatische Synchronisation ist ein Backend-Task. Der Endpoint `POST /users/sync_all` existiert zusaetzlich als manueller Trigger.
- Challenge-Jahr und Challenge-Monat werden in Teilen der Backend-Logik konfiguriert. Bei einer neuen Challenge sollten `CHALLENGE_MONTH`, Datumslogik und die feste Konfiguration in `routes/activities.py` gemeinsam geprueft werden.
- Vor Produktionsdeployments muessen CORS-Domains, Strava-Redirect-URL, `DATABASE_URL` und `ADMIN_PASSWORD` zusammenpassen.