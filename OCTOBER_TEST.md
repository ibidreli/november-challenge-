# Oktober-Test mit der bestehenden Strava-App

Der Test erhält eine eigene PostgreSQL-Datenbank und einen Docker-Web-Service. Dieser liefert Frontend und Backend unter **test.novjogcha.ch** aus. Die bestehenden Dienste `frontend`, `backend` und `database` bleiben bestehen. Keine zweite Strava-App nötig. Beim Anlegen der zusätzlichen Render-Ressourcen den angezeigten Tarif prüfen.

## 1. Änderungen pushen

```powershell
git status
git add .
git diff --cached --stat
git commit -m "Add isolated October challenge rehearsal"
git push origin main
```

Vor dem Commit prüfen, dass keine geheimen `.env`-Dateien enthalten sind. Das normale Deployment bleibt im November. Beim vorhandenen Backend **CHALLENGE_TEST_MODE nicht auf 1 setzen**. Die Migration ergänzt Kalenderfelder und erhält bestehende November-Auslosungen und Ergebnisse.

## 2. Strava-Abrufe auf der Hauptseite pausieren

Nachdem das bestehende Backend den neuen Commit erfolgreich deployt hat: **Render → bestehendes backend → Environment → Edit → STRAVA_SYNC_ENABLED=0**, speichern und deployen.

Diese Pause stoppt Hintergrundimport, manuelle Synchronisation und Webhook-Import. `ENABLE_BACKGROUND_SYNC=0` allein würde Webhooks nicht stoppen. Website-Sitzungen und Gast-Läufergruppen bleiben verfügbar. Verwende dein Strava-Konto während des Tests auf der Testseite.

Strava erneuert Refresh-Tokens; ältere Tokens desselben Kontos und derselben App können dadurch ungültig werden. Deshalb ruft während des Tests nur der Testdienst Aktivitäten ab. Nach dem Test verbindest du dein Konto auf der Hauptseite einmal neu. [Strava-Token-Erneuerung](https://developers.strava.com/docs/authentication/)

## 3. Testdatenbank erstellen

**Render → New → Postgres**:

| Feld | Wert |
| --- | --- |
| Name | `november-october-test-db` |
| Database | `challenge_october_test` |
| Region | Dieselbe wie beim neuen Test-Web-Service, z.B. Oregon |
| PostgreSQL-Version | `17` |

Danach die **Internal Database URL** dieser neuen Datenbank kopieren. Nicht die URL der bestehenden produktiven `database` verwenden.

## 4. Test-Web-Service erstellen

**Render → New → Web Service → dasselbe Git-Repository auswählen**:

| Feld | Wert |
| --- | --- |
| Name | `november-october-test` |
| Branch | `main` |
| Runtime | `Docker` |
| Root Directory | leer |
| Dockerfile Path | `./Dockerfile.test` |
| Docker Build Context Directory, falls angezeigt | `.` |
| Docker Command | leer |
| Health Check Path | `/healthz` |
| Region | Dieselbe wie die Testdatenbank |

Unter **Environment** setzen:

| Variable | Wert |
| --- | --- |
| `DATABASE_URL` | Internal Database URL von `november-october-test-db` |
| `ADMIN_PASSWORD` | Selbst gewähltes Passwort für den Test-Admin |
| `CHALLENGE_YEAR` | `2026` |
| `CHALLENGE_TEST_MODE` | `1` |
| `CHALLENGE_TEST_START_DATE` | `2026-10-01` |
| `CHALLENGE_TEST_PERIOD_DAYS` | `8,7,7,7` |
| `FRONTEND_URL` | `https://test.novjogcha.ch` |
| `STRAVA_REDIRECT_URI` | `https://test.novjogcha.ch/auth/callback` |
| `STRAVA_CLIENT_ID` | Dieselbe Client-ID wie beim produktiven Backend |
| `STRAVA_CLIENT_SECRET` | Dasselbe Client Secret wie beim produktiven Backend |
| `STRAVA_SYNC_ENABLED` | `1` |
| `ENABLE_BACKGROUND_SYNC` | `1` |
| `REQUIRE_POSTGRES` | `1` |
| `COOKIE_SECURE` | `1` |
| `FORWARDED_ALLOW_IPS` | `*` |
| `LOAD_ENV_FILE` | `0` |
| `ENABLE_DEBUG_ROUTES` | `0` |

Keine produktiven Access-/Refresh-Tokens kopieren. Keine `VITE_API_BASE_URL` setzen: Das Test-Image baut relative API-Adressen ein. `frontend/.env.production` bleibt unverändert. Auf dem Testdienst keine Webhook-Subscription konfigurieren; der Test importiert nach Anmeldung, auf Knopfdruck und alle 30 Minuten. Die bestehende produktive Subscription bleibt bestehen, ihre Importarbeit ist während der Pause deaktiviert.

## 5. Testadresse und bestehende Strava-App

Beim **neuen Testdienst → Settings → Custom Domains → Add Custom Domain** `test.novjogcha.ch` hinzufügen.

Beim DNS-Anbieter einen zusätzlichen Eintrag erstellen: **Typ CNAME**, **Name test**, **Ziel der von Render angezeigte Host des Testdienstes ohne https://**. Bestehende DNS-Einträge beibehalten. In Render **Verify** anklicken und auf das HTTPS-Zertifikat warten. [Render-Domains](https://render.com/docs/custom-domains)

In [Strava → Settings → My API Application](https://www.strava.com/settings/api) die **Authorization Callback Domain** der bestehenden App auf **novjogcha.ch** setzen, ohne `https://` oder Pfad. Damit liegen die produktive Rücksprungadresse `api.novjogcha.ch/auth/callback` und die Testadresse `test.novjogcha.ch/auth/callback` innerhalb der registrierten Domain. Die Client-ID und das Secret bleiben gleich. [Strava-OAuth](https://developers.strava.com/docs/authentication/)

## 6. Probelauf

1. `https://test.novjogcha.ch/healthz` muss `status: ok` melden.
2. `https://test.novjogcha.ch` öffnen: gelber Hinweis **Testumgebung**, Oktober-Daten und vorhandenes Logo.
3. `/admin` mit dem **ADMIN_PASSWORD des Testdienstes** öffnen.
4. Testkalender **vor der ersten Veröffentlichung** festlegen. Standard: 1.–8., 9.–15., 16.–22. und 23.–29. Oktober, Abschluss am 30. Oktober. Weiterhin 8/7/7/7 Ziele und standardmässig 15 km für das Finale.
5. Für Zeitraum 1 beispielsweise `5,6,9,14,19,24,27,29` manuell eintragen. Entwurf speichern → öffentliche Seite prüfen → veröffentlichen. Die Auslosung erfolgt weiterhin im echten Leben. Eine erstmalige Veröffentlichung nach Periodenbeginn wertet vorhandene Läufe nachträglich.
6. Mit deinem echten Strava-Konto anmelden und die Aktivitätsfreigabe erlauben. Bestehende Oktober-Läufe innerhalb des Kalenders werden importiert. Auf **Strava synchronisieren** drücken, warten und gegebenenfalls neu laden.
7. Feldchen, Rangliste, Diagramm und Admin-Aktivitäten vergleichen. Wiederholter Import darf keine doppelten Punkte erzeugen. Am nächsten Tag nochmals prüfen, damit Token-Erneuerung und Angemeldetbleiben getestet werden.
8. Gast-Läufergruppe mit Kartenpunkt erstellen, in einem anderen Browser teilnehmen, nach Neuladen bearbeiten/absagen. Dasselbe am Handy prüfen.

### Wertung ohne zusätzliche echte Läufe prüfen

Im Test-Admin einen **manuellen Testläufer** anlegen. Für diesen Teilnehmer unter Aktivitäten vergangene Tage erfassen:

| Datum | Gelaufen | Erwartetes Feld |
| --- | --- | --- |
| 1.10.2026 | 35 km | 29 km |
| 2.10.2026 | 30 km | 27 km |
| 3.10.2026 | 7 km | 6 km |
| 4.10.2026 | 4 km | keines |

Ergebnis bei obiger Auslosung: **3 Distanzen, 62 gewertete km**. Nur die Website-Testdatenbank wird verändert; keine künstlichen Aktivitäten werden in Strava angelegt. Manuelle Korrekturen auf deinem echten Testprofil würden dessen Strava-Wertung für den jeweiligen Tag ersetzen; deshalb den separaten manuellen Teilnehmer verwenden.

### Wochenwechsel und Finale sofort testen

Vor Veröffentlichung im Testkalender beispielsweise **Beginn 1.10.2026, vier Perioden mit je 1 Tag** wählen: Perioden am 1., 2., 3. und 4. Oktober, Finale am 5. Oktober. Damit kannst du alle Abschnitte mit bereits vergangenen echten Läufen oder manuellen Testdaten prüfen. Weiterhin höchstens eine Wertung pro Tag; in verkürzten Perioden können entsprechend nicht alle Ziele erledigt werden.

Nach Veröffentlichung ist der Kalender gesperrt. Für einen weiteren Durchgang mit anderem Kalender eine neue leere **Testdatenbank** anbinden. Render-Kalenderwerte dienen nur der Erstinitialisierung; ein Neustart überschreibt den gespeicherten Kalender nicht. Die Serveruhr und echte Strava-Datumswerte werden nicht verändert.

## 7. Strava-Fehler prüfen

**Testdienst → Logs → Strava sync failed** zeigt nun HTTP-Status und Endpunkt ohne Tokens oder Antwortkörper.

| Status | Nächster Schritt |
| --- | --- |
| `401` | Strava-Verbindung auf der Testseite erneuern |
| `403` | Aktivitätsfreigabe bei erneuter Verbindung erlauben; App-Zugriff prüfen |
| `400` am `/oauth/token` | Client-ID/Secret und Verbindung prüfen; keine alten Tokens zwischen Diensten kopieren |
| `429` | Strava-Anfragelimit abwarten |
| `5xx` | Später erneut versuchen |

Ein Datum vor November verursacht für sich keinen HTTP-Fehler. Der bisherige Logeintrag ohne Status reicht nicht zur Diagnose. Den echten Strava-Abruf können wir erst nach Anmeldung und Einrichtung im Render-Konto abschliessend bestätigen.

## 8. Vor November zurückwechseln

1. **Testdienst → Environment → STRAVA_SYNC_ENABLED=0**, speichern und deployen.
2. **Produktives backend → Environment → STRAVA_SYNC_ENABLED=1** und **ENABLE_BACKGROUND_SYNC=1**, speichern und deployen.
3. Produktiv **CHALLENGE_TEST_MODE=0** lassen; `CHALLENGE_TEST_START_DATE` und `CHALLENGE_TEST_PERIOD_DAYS` dort nicht setzen.
4. Auf `https://www.novjogcha.ch` dein Konto einmal erneut mit Strava verbinden.
5. Am produktiven API-Host `/challenge` prüfen: `test_mode=false`, `starts_on=2026-11-01`, `finale_date=2026-11-30`.
6. Produktive Auslosungen selbst eintragen/veröffentlichen. Keine Testergebnisse übernehmen.

Die Callback Domain `novjogcha.ch` kann bestehen bleiben. Die produktive Redirect-URI bleibt `https://api.novjogcha.ch/auth/callback`. Die zusätzlichen Testressourcen können nach Abschluss in Render entfernt werden.

## Automatische Prüfung

```powershell
.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
```

```powershell
cd frontend
npm test
npm run build
```

Tests verwenden temporäre Datenbanken und simulierte Strava-Antworten. Die Browserprüfung testet Oktober-Admin, Wertung, Feldchen, Kalender-Sperre, Diagramm und mobile Darstellung gegen ein echtes lokales Backend. Produktionsdaten und echte Strava-Aktivitäten werden dabei nicht verändert.
