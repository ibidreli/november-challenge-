# Bereinigung und erhaltene Historie

Die Anwendung verwendet jetzt einen API-Client im Frontend, eine zentrale Wochenwertung und einen gemeinsamen Strava-Importdienst. Die bisherigen mehrfachen Berechnungen in OAuth, Aktivitäten-Routen, Webhook und Scheduler wurden ersetzt. Ungenutzte Login-Komponente, alte Admin-CSS, leere Root-NPM-Datei, alte Implementierungszusammenfassung und die funktionslose nginx-Vorlage wurden entfernt. Docker Compose startet nur noch die lokal benötigten Dienste.

Die alten öffentlichen Wartungs-/Prozess-/Debug-Routen und der Browser-Token-/OTP-Login wurden entfernt. Nur benötigte Challenge-, Auth-, Gruppen- und Admin-Schnittstellen bleiben. Diagnose ist ausdrücklich opt-in und geschützt. Die Anwendung erstellt keine verwalteten Datenbanken und verändert Render-URLs nicht mehr durch erratene Regionsnamen. Fehler führen nicht zu einem versteckten SQLite-Fallback in Produktion.

`backend/dev.db` bleibt lokal bestehen, ist aber aus der Git-Verfolgung genommen. Abhängigkeiten des Frontends sind über `frontend/package-lock.json` reproduzierbar. `.env` und lokale Testdaten sind ignoriert. `output/ui-proposal/` ist der frühere, vom Nutzer freigegebene Entwurf; die aktive Anwendung liegt vollständig unter `frontend/src`, nicht in dieser HTML-Datei.

Bewusst erhalten: historische `claims`, `users.slots`, `users.total_score` und vorhandene Aktivitäten. Die neue Tabelle `challenge_claims` speichert die editionsbezogene Wochenwertung. So überschreibt die Umstellung keine Resultate aus 2025. Beide Dockerfiles sind bewusst vorhanden, damit Render sowohl einen Root-Build als auch einen Build ab `backend/` verwenden kann.

Die Entwickleranleitung, Admin-Anleitung, API-Liste und Render-Einstellungen sind auf die aktuelle Implementierung aktualisiert. Neue Änderungen an der Datenbank müssen sowohl in Modellen als auch in der versionierten Migration berücksichtigt werden.
