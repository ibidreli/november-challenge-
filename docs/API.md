# API-Verzeichnis

Interaktive Schemas und Beispiele: Backend `/docs`. Öffentliche API liefert nur veröffentlichte Ziele und berechnete Resultate. JSON-Schreibanfragen von Browsern müssen von einem konfigurierten Frontend-Ursprung stammen.

| Methode | Pfad | Anmeldung / Zweck |
| --- | --- | --- |
| GET | `/healthz` | Bereitschaft inklusive echter DB-Abfrage; 503 bei Fehler |
| GET | `/challenge` | Jahr, Schweizer Datum, Finale, veröffentlichte Wochen |
| GET | `/challenge/statistics` | Gewertete Gesamtkilometer und täglicher kumulativer Verlauf |
| GET | `/users/` | Rangliste, Punkte, 30 Feldzustände pro Person |
| GET | `/users/me` | Website-Cookie; persönliche Übersicht, Sync-Zeit/Fehler |
| POST | `/users/me/sync` | Website-Cookie; Import im Hintergrund anstossen (202) |
| GET | `/auth/login?return_to=/` | OAuth mit geprüftem State und sicherem Rücksprung |
| GET | `/auth/callback` | Strava-Callback, setzt eigene Sitzung, keine Tokens im Redirect |
| POST | `/auth/logout` | Eigene Sitzung widerrufen |
| GET | `/auth/webhook` | Strava-Verifikation mit `hub.*`-Parametern |
| POST | `/auth/webhook` | Konfigurierte Subscription; Hintergrund-Abgleich |
| GET | `/community` | Aktive Läufe; Gast-Cookie, eigene Bedienrechte, Serverzeit |
| POST | `/community` | Gast/Strava: Lauf mit Ersteller als Teilnehmer erzeugen |
| PUT / DELETE | `/community/{id}` | Eigentümer: bearbeiten / absagen |
| POST | `/community/{id}/participants` | Gast/Strava: idempotent teilnehmen, Body `{name}` |
| DELETE | `/community/{id}/participants/me` | Eigene Teilnahme entfernen |
| POST | `/admin/login` | Body `{password}`; persistenter Admin-Token, zwei Stunden |
| POST | `/admin/logout` | Admin-Sitzung widerrufen |
| GET | `/admin/challenge` | Inklusive unveröffentlichter Entwürfe |
| PUT | `/admin/challenge/finale` | Body `{km}` |
| PUT | `/admin/challenge/periods/{1..4}` | Entwurf, Body `{distances:[...]}` |
| POST | `/admin/challenge/periods/{1..4}/publish` | Gleicher Body; veröffentlichen und neu werten |
| GET / POST | `/admin/users` | Teilnehmer lesen / mit `{name}` anlegen |
| PUT / DELETE | `/admin/users/{id}` | Name mit `{name}` ändern / Teilnehmer samt Daten löschen |
| GET / POST | `/admin/activities` | Aktivitäten des aktiven Kalenders / manuelle Tageskorrektur |
| PUT | `/admin/challenge/test-calendar` | Nur Testumgebung: `{starts_on, period_days:[8,7,7,7]}`, vor erster Veröffentlichung |
| PUT / DELETE | `/admin/activities/{id}` | Manuelle Aktivität ändern / Aktivität ausschliessen |
| POST | `/admin/activities/{id}/restore` | Admin-Ausschluss rückgängig machen |
| POST | `/admin/sync` | Vollständigen Strava-Import im Hintergrund starten (202) |
| GET | `/admin/community` | Aktive Läufergruppen moderieren |
| DELETE | `/admin/community/{id}` | Als Admin absagen |

Alle Admin-Pfade ausser `/admin/login` benötigen `X-Admin-Token`. Spieler verwenden den `HttpOnly`-Cookie `nc_session`, Gäste für Eigentum/Teilnahme `nc_guest`. Keine Strava-Bearer-Tokens oder Login-Geheimnisse in Query-Parametern.

Manuelle Aktivität: `{user_id, date:"2026-11-01", distance_km:7}`. Datum darf nicht in der Zukunft liegen. Eine Tageskorrektur ersetzt Strava an diesem Tag.

Gruppenlauf: `{name, distance_km, pace_seconds, starts_at:"2026-11-10T17:30:00Z", latitude, longitude, meeting_point}`. Startzeit muss eine Zeitzone enthalten, in der Zukunft und innerhalb eines Jahres liegen. Pace 60–1800 Sekunden/km. `expires_at` wird ausschliesslich vom Server als Start + 3 Stunden gesetzt. Abgelaufene/abgesagte Läufe sind nicht mehr beitretbar.

Schreibbegrenzungen pro IP, persistent und atomar: 5 Lauf-Erstellungen/Stunde, 60 Teilnahmen/Stunde, 6 persönliche Synchronisationsstarts/Stunde, 20 Admin-Loginversuche/Stunde, 30 OAuth-Starts/Stunde. Das Frontend zeigt 429-Fehler verständlich an.

Optionale Diagnose-Endpunkte aus `routes/diagnostics.py` existieren nur bei `ENABLE_DEBUG_ROUTES=1` und verlangen einen Admin-Token. Die früheren doppelten Import-/Prozess-/Debug-/Token-Endpunkte wurden entfernt.
