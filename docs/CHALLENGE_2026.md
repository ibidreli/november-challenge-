# Umgesetzte Regeln für November 2026

Vier Zeiträume: **1.–8., 9.–15., 16.–22. und 23.–29. November** mit **8 / 7 / 7 / 7** Distanzen. Die realen Auslosungen finden am **31.10., 8.11., 15.11. und 22.11.** statt. Der Admin trägt die Resultate ein und veröffentlicht sie bewusst.

Jede ganze Distanz von 1–30 km wird genau einmal verteilt. Eine im Admin einstellbare Distanz, standardmässig **15 km**, bleibt für den **30.11.** reserviert. Unveröffentlichte Entwürfe sind öffentlich nicht abrufbar.

Im Admin kann eine Auslosung mit **Auslosung zurücksetzen** auch nach Beginn der Woche gelöscht werden. Dabei werden die Distanzen freigegeben und die Wertungen dieser Woche entfernt. Die Läufe bleiben gespeichert und werden nach erneuter Veröffentlichung mit den neuen Distanzen gewertet. Andere Wochen, der Abschlusslauf und andere Editionen bleiben erhalten.

## Wertung

- Lauftag und Wochenzuordnung gelten in `Europe/Zurich`.
- Pro Tag zählt der längste **einzelne** Lauf, keine Summe mehrerer Aktivitäten.
- Ein Lauf erledigt die grösste noch offene Distanz seiner Woche, die kleiner oder gleich der tatsächlich gelaufenen Distanz ist. Es wird nicht aufgerundet.
- Beispiel `[5,6,9,14,19,24,27,29]`: 35 km → 29; am nächsten Tag 30 km → 27; 7 km → 6; 4 km → kein Feld.
- Offene Ziele gehen nicht in die nächste Woche über. Zukunftsaktivitäten werden nicht vor ihrem tatsächlichen Lauftag gewertet.
- Am 30.11. erfüllt ein Lauf ab der eingestellten Abschlussdistanz das Finale automatisch, unabhängig von einer Gruppen-Teilnahme.
- Der Rang ergibt sich aus der Summe erledigter Zieldistanzen. Bei Gleichstand gleicher Rang (1, 1, 3).
- Das gemeinsame Diagramm summiert dieselben gewerteten Kilometer nach Lauftag, nicht die Strava-Rohkilometer.
- Spätere Uploads, Änderungen und Löschungen lösen eine chronologische Neuberechnung aus. Wiederholte Importe erzeugen keine zusätzlichen Punkte.
- Eine explizite manuelle Admin-Tageskorrektur hat Vorrang vor Strava. Bei mehreren manuellen Korrekturen desselben Tages zählt die längste.

## Oberfläche

Öffentliche Übersicht: kurze Erklärung, auffälliger Strava-Login, gemeinsamer Kilometerverlauf. Angemeldet: persönliche Anzeige oberhalb des weiterhin sichtbaren Diagramms. Alle 30 nummerierten Kilometerfelder bleiben an festen Positionen; offene Wochenziele erscheinen zusätzlich als klarer Hinweis. Antippen eines Feldes erklärt Status/Laufdatum.

Rangliste: kompakte Feldchen pro Person, auf Desktop gemeinsame Nummernzeile. Auf Handy ein kleines Raster aus drei Zeilen; Antippen öffnet die nummerierten Details. Immer höchstens eine Person ausgeklappt.

Läufergruppen: Karte mit Startpunkten, Erstellen und Teilnehmen auch als Gast mit frei eingegebenem Namen. Name, km, Pace, Schweizer Startzeit und ein Kartenpunkt samt Beschreibung sind Pflicht. Ersteller ist automatisch Teilnehmer. Eigene Teilnahme/Läufe lassen sich über einen persistenten Browser-Cookie verwalten, optional zusätzlich über Strava. Sichtbarkeit endet exakt drei Stunden nach Start, auch ohne Bereinigungsjob oder Backend-Neustart. Namen und Koordinaten werden öffentlich angezeigt; Identitätsschlüssel werden nicht ausgeliefert.

## Daten und Betrieb

Neue Tabellen: `challenge_editions`, `challenge_periods`, `distance_targets`, `challenge_claims`, `auth_sessions`, `oauth_states`, `community_runs`, `community_participants`, `request_limits`. Zusätzliche Aktivitäts-/Token-/Sync-Metadaten an bestehenden Tabellen. Historische Resultate bleiben separat erhalten.

Website-Anmeldung: eigener zufälliger Cookie, serverseitig nur als SHA-256-Hash gespeichert, 90 Tage mit Verlängerung bei Nutzung. Strava-Token-Erneuerung hat keinen Einfluss auf diese Sitzung. Gast-Cookie ebenfalls 90 Tage. Admin-Sitzung zwei Stunden. Render benötigt dafür die API auf `api.novjogcha.ch` und die Frontend-Seite auf derselben Hauptdomain; Details in [Deployment](../DEPLOYMENT_CHECKLIST.md).

PostgreSQL-Sperren und eindeutige Constraints schützen die Wertung gegen gleichzeitige Importe. Synchronisationen eines Teilnehmers laufen nicht parallel. Ein Scheduler gleicht alle 30 Minuten den ganzen November ab; ein optionaler Webhook beschleunigt Änderungen. Hintergrundarbeit blockiert den FastAPI-Eventloop nicht. Fehlgeschlagene Abrufe löschen keine bestehenden Ergebnisse.
