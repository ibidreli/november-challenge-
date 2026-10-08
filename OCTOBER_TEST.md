# Oktober direkt auf der bestehenden Website testen

Du verwendest weiterhin **novjogcha.ch**, die vorhandenen Render-Dienste und dieselbe Strava-App. Die bestehende Datenbank speichert Auslosungen und Punkte für Oktober und November getrennt. Strava-Verbindungen und Website-Anmeldungen bleiben gemeinsam bestehen.

## Einmalig die vereinfachte Version veröffentlichen

Im Projektordner:

```powershell
git add .
git commit -m "Simplify October testing on the existing website"
git push origin main
```

Auf erfolgreiche Deployments von **backend** und **frontend** warten. Bei ausgeschaltetem Auto-Deploy jeweils **Manual Deploy → Deploy latest commit** verwenden. Die Datenbankmigration läuft automatisch; keine Datenbank neu anlegen oder zurücksetzen.

## Oktober einschalten

**Render → bestehendes backend → Environment → Edit**:

```dotenv
CHALLENGE_MONTH=10
```

**CHALLENGE_YEAR bleibt 2026.** Speichern und das Backend deployen. Die Website danach neu laden. `https://api.novjogcha.ch/challenge` zeigt `month: 10` und `starts_on: 2026-10-01`.

Auf der normalen Website erscheint **Oktober-Probelauf**. Der Kalender lautet 1.–8., 9.–15., 16.–22. und 23.–29. Oktober; der Abschluss ist am 30. Oktober. Die Verteilung bleibt 8/7/7/7 Ziele.

1. Auf der normalen Website `/admin` öffnen, mit deinem bisherigen Admin-Passwort anmelden und die Oktober-Auslosung manuell eintragen/veröffentlichen. Eine erstmalige Veröffentlichung ist auch nach Beginn des Zeitraums möglich.
2. Mit Strava anmelden oder bei bestehender Anmeldung **Strava synchronisieren** drücken. Deine bisherigen Oktober-Läufe werden importiert; es zählt weiterhin der längste einzelne Lauf pro Tag.
3. Feldchen, Rangliste, Diagramm und Admin-Aktivitäten vergleichen. Nach erneutem Import dürfen keine doppelten Punkte entstehen.
4. Läufergruppen und Karte auf Computer und Handy ausprobieren.

Für einen gezielten Wertungstest kannst du im Admin einen manuellen Teilnehmer anlegen und vergangene Oktober-Läufe eintragen. Dabei werden keine Aktivitäten in Strava angelegt. Manuelle Teilnehmer sind in beiden Monaten sichtbar, ihre Kilometer werden nur im jeweiligen Monat gewertet. Nicht mehr benötigte manuelle Testteilnehmer kannst du später im Admin löschen.

## Auf November zurückwechseln

Beim **selben backend → Environment** ändern:

```dotenv
CHALLENGE_MONTH=11
```

Speichern, Backend deployen und Website neu laden. Jetzt gelten wieder 1.–30. November. Bereits vorbereitete November-Auslosungen und November-Ergebnisse sind wieder sichtbar; Oktober-Punkte werden nicht übernommen. Der Strava-Login bleibt bestehen. Wenn du später nochmals auf `10` wechselst, sind deine Oktober-Auslosungen und Ergebnisse weiterhin vorhanden.

## Alte Testkonfiguration entfernen

Falls du sie aus der vorherigen Anleitung bereits gesetzt hast, beim bestehenden Backend diese alten Variablen entfernen: `CHALLENGE_TEST_MODE`, `CHALLENGE_TEST_START_DATE`, `CHALLENGE_TEST_PERIOD_DAYS`, `STRAVA_SYNC_ENABLED` und `SERVE_FRONTEND_DIRECTORY`. Sie werden nicht mehr verwendet. Für automatische Aktualisierung `ENABLE_BACKGROUND_SYNC=1` lassen.

Frontend-Adresse, `DATABASE_URL`, `VITE_API_BASE_URL`, Strava-Client-ID, Secret und die produktive Redirect-URI bleiben unverändert. Keine weitere Domain oder Strava-App einrichten. Falls bereits zusätzliche Testdienste angelegt wurden, werden sie für diesen Ablauf nicht mehr benötigt.

Ein weiterhin auftretender Strava-HTTP-Fehler ist separat zu prüfen: **backend → Logs → Strava sync failed**. Der Logeintrag nennt Status und Endpunkt, ohne Tokens auszugeben. Die Kalenderumschaltung behebt fehlende Strava-Berechtigungen oder ungültige Zugangsdaten nicht.
