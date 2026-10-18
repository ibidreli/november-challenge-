# Ladezeit und Jogger-Animation

Die Übersicht lädt Konfiguration, Anmeldung und Statistik parallel. Beim ersten Anzeigen wartet sie auf die Prüfung der Anmeldung, damit die persönliche Übersicht oder die Erklärung für Gäste von Anfang an oberhalb der Statistik steht. So wird eine bereits sichtbare Statistik nicht nach unten geschoben. Der obere Bereich erscheint auch dann bereits, wenn die Statistik noch lädt. Die Rangliste wird erst beim Öffnen des entsprechenden Tabs abgefragt. Beim Aktualisieren bleiben vorhandene Inhalte sichtbar. Laufgruppen und Admin-Code inklusive Karten-CSS werden erst beim Öffnen geladen. Gleichzeitige identische öffentliche Anfragen teilen sich eine laufende Anfrage; Antworten werden nicht dauerhaft zwischengespeichert.

Die Rangliste verwendet fünf SQL-Abfragen unabhängig von der Teilnehmerzahl. Zuvor wurde die Edition zusätzlich pro Teilnehmer abgefragt. Die Statistik summiert Kilometer direkt in der Datenbank. Grössere Antworten werden mit Gzip komprimiert, sofern der Client dies unterstützt. DM Sans liegt mit Lizenz unter `frontend/public/fonts`; externe Google-Fonts-Anfragen entfallen.

Der Jogger verwendet einen gemeinsamen SVG-Laufzyklus für Arme, Beine und Körper. Kniepositionen werden aus festen Beinlängen und der Fussbahn berechnet. Die Animation läuft ohne React-Updates pro Bild und pausiert bei `prefers-reduced-motion`.

## Veröffentlichen und messen

1. Änderungen einschliesslich der neuen Dateien committen und auf den mit Render verbundenen Branch pushen. Frontend **und** Backend müssen den neuen Commit deployen. Keine neuen Umgebungsvariablen oder Datenbankmigrationen erforderlich.
2. Chrome DevTools → Network → Disable cache aktivieren, Seite neu laden. Unter Übersicht dürfen `/challenge`, `/challenge/statistics` und `/users/me` erscheinen; `/users/` erst beim Öffnen der Rangliste. Eine `401` bei `/users/me` ist bei Gästen normal.
3. In einer API-Antwort unter Headers steht `Server-Timing: app;dur=…` (Millisekunden im Backend, ohne Übertragung und Browser-Rendering). Viel höhere Gesamtdauer bei kleiner Backend-Dauer deutet auf Netzwerk, Proxy oder Verbindungsaufbau hin. Hohe Backend-Dauer spricht für Datenbank oder Serverauslastung. Grössere Antworten sollten `Content-Encoding: gzip` haben, sofern Render die Kompression nicht selbst übernimmt.
4. LCP auf derselben Seite, mit denselben Cache-/Drosselungsbedingungen mehrfach vergleichen. Ein Aufruf direkt nach längerer Pause und weitere Aufrufe sollten separat betrachtet werden. Lokale Testzeiten sind kein Vergleichswert für produktive Render-Ladezeiten.

## Falls Render weiter langsam antwortet

- Render → Backend → Settings → Instance Type prüfen. Ein Free-Web-Service schläft nach 15 Minuten ohne Traffic ein; der nächste Start dauert laut Render ungefähr eine Minute. Eine kostenpflichtige Backend-Instanz verhindert dieses Einschlafen. Dafür muss der **Service-Tarif**, nicht der Workspace-Tarif, geändert werden. [Render-Dokumentation](https://render.com/docs/free#spinning-down-on-idle)
- Render → PostgreSQL → Info → Connections: Bei Backend und Datenbank in derselben Region die **Internal Database URL** als `DATABASE_URL` des Backends verwenden. Beide Dienste sollten dieselbe Region haben. Werte mit Zugangsdaten nicht in Git oder Screenshots veröffentlichen. [Render-Dokumentation](https://render.com/docs/postgresql-creating-connecting#connect-to-your-database)
- Eine andere Region oder mehr Rechenleistung erst nach diesen Messungen erwägen. Die bisherigen Screenshots belegen keine bestimmte Render-Konfiguration. Diese Änderungen am Hosting wurden nicht automatisch vorgenommen.

## Lokale Prüfungen

Im Projektordner: `.venv\Scripts\python.exe -m unittest discover -s backend/tests -p test_api.py`. In `frontend`: `npm test` und `npm run build`. Die Tests verwenden isolierte Datenbanken und rufen Strava nicht auf. Die zusätzlichen Prüfungen decken konstante SQL-Abfragezahl, Kompression, verzögerte Statistik, Wiederholen nach Fehlern, Laden der Rangliste bei Bedarf und reduzierte Bewegung ab.
