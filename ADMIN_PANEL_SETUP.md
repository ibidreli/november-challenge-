# Administration

Öffne `/admin` auf der Website und melde dich mit `ADMIN_PASSWORD` an. Das Passwort wird als JSON übertragen, nicht als URL-Parameter. Die Admin-Sitzung liegt gehasht in PostgreSQL, bleibt nach einem Backend-Neustart gültig und läuft nach zwei Stunden ab. Abmelden widerruft sie sofort.

## Challenge vorbereiten

1. Abschlussdistanz einstellen, zunächst **15 km**. Zulässig sind ganze Zahlen 1–30. Die Zahl ist für den 30.11. reserviert.
2. Nach der echten Auslosung im passenden Wochenfeld die Distanzen mit Kommas oder Leerzeichen eintragen.
3. **Entwurf speichern** reserviert die Zahlen intern. Teilnehmer sehen sie noch nicht.
4. **Veröffentlichen** zeigt sie öffentlich und wertet bereits importierte Läufe dieses Zeitraums neu.

| Woche | Zeitraum 2026 | Anzahl | Auslosung |
| --- | --- | --- | --- |
| 1 | 1.–8.11. | 8 | 31.10. |
| 2 | 9.–15.11. | 7 | 8.11. |
| 3 | 16.–22.11. | 7 | 15.11. |
| 4 | 23.–29.11. | 7 | 22.11. |

Beispiel Woche 1: `5, 6, 9, 14, 19, 24, 27, 29`. Der Topf zeigt alle noch nicht reservierten Distanzen. Doppelte Zahlen, falsche Anzahl oder die Abschlussdistanz werden abgewiesen. Jede Distanz 1–30 kommt über vier Wochen und Finale genau einmal vor.

Eine veröffentlichte Woche kann vor ihrem Start geändert oder wieder als Entwurf gespeichert werden. Ab Beginn ist sie gesperrt, damit niemand rückwirkend andere Ziele erhält. Eine noch unveröffentlichte Woche kann auch verspätet veröffentlicht werden: Die Wertung verwendet den ursprünglichen Lauftag. Die Abschlussdistanz lässt sich vor dem 30.11. ändern, sofern die neue Zahl noch frei ist. Deshalb diese möglichst vor der ersten Auslosung festlegen.

## Teilnehmer und Korrekturen

Teilnehmer mit Strava werden beim ersten Login automatisch hinzugefügt. Ohne Strava kannst du unter **Teilnehmer** einen Namen hinzufügen und später Läufe manuell eintragen. Namen lassen sich korrigieren.

Unter **Aktivitäten** stehen die letzten 1000 Aktivitäten der aktiven November-Edition. Eine manuelle Eingabe ist eine **Tageskorrektur**: Sie ersetzt an diesem Tag Strava, auch wenn dort ein längerer Lauf steht. Bei mehreren manuellen Einträgen zählt deren längster. Ohne Korrektur zählt der längste einzelne Strava-Lauf. Die Wertung wird sofort über den ganzen Monat neu berechnet; dadurch bleiben auch später hinzugefügte Läufe korrekt.

**Ausschliessen** entfernt eine Aktivität aus der Wertung, erhält aber die Rohdaten. **Wieder werten** macht das rückgängig. Wird eine manuelle Tageskorrektur ausgeschlossen, zählt wieder Strava. Eine ausgeschlossene Strava-Aktivität wird beim nächsten Import nicht automatisch wieder aktiviert. Gelaufene Kilometer eingeben, nicht den gewünschten Feldwert.

**Strava abrufen** startet einen vollständigen Import im Hintergrund; danach Daten neu laden. Strava-Korrekturen am ursprünglichen Lauf möglichst in Strava durchführen. Das endgültige Löschen eines Teilnehmers entfernt dessen Daten inklusive historischer Aktivitäten/Resultate und benötigt deshalb eine Bestätigung im Admin.

## Läufergruppen

Teilnehmer verwalten eigene Läufe selbst. Unter **Läufergruppen** kannst du als Admin einen problematischen Lauf absagen. Das entfernt ihn sofort aus der öffentlichen Anzeige. Ereignisse werden ohnehin exakt drei Stunden nach der Startzeit ausgeblendet.
