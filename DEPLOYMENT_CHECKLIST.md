# Bestehende Render-Dienste aktualisieren

Für einen Oktober-Probelauf auf derselben Website genügt `CHALLENGE_MONTH=10` am bestehenden Backend; mit `11` zurückwechseln. Ablauf: [OCTOBER_TEST.md](OCTOBER_TEST.md). Die folgende Anleitung beschreibt die November-Seite.

Die vorhandene Struktur bleibt erhalten: **frontend** als Static Site, **backend** als Docker-Web-Service, **database** als PostgreSQL. Es werden keine neuen Render-Dienste benötigt. Die folgenden Einstellungen sind vorbereitet; DNS und Render müssen im jeweiligen Konto gesetzt werden.

## 1. API unter derselben Hauptdomain erreichbar machen

Frontend: `https://www.novjogcha.ch` · Backend: **`https://api.novjogcha.ch`**.

Damit liegen beide Dienste für Browser-Cookies auf derselben Site. Eine fremde `onrender.com`-API neben `novjogcha.ch` ist für zuverlässige Anmeldung mit `SameSite=Lax` ungeeignet. Der Code verwendet absichtlich keine Strava-Tokens im Browser als Ausweichlösung.

Im bestehenden Backend-Service unter **Settings → Custom Domains** `api.novjogcha.ch` hinzufügen. Beim DNS-Anbieter den von Render angegebenen CNAME-Zielwert eintragen (den tatsächlichen bestehenden Backend-Host verwenden, keine URL mit `https://`). Danach in Render verifizieren. Render stellt das TLS-Zertifikat bereit. Anleitung: [Render Custom Domains](https://render.com/docs/custom-domains).

## 2. Backend-Umgebungsvariablen

| Variable | Wert / Zweck |
| --- | --- |
| `DATABASE_URL` | **Internal Database URL** der bestehenden PostgreSQL-Datenbank in derselben Render-Region, unverändert übernehmen |
| `REQUIRE_POSTGRES` | `1` |
| `FRONTEND_URL` | `https://www.novjogcha.ch` |
| `CUSTOM_DOMAIN` | `https://novjogcha.ch` |
| `COOKIE_SECURE` | `1` |
| `FORWARDED_ALLOW_IPS` | `*` hinter dem Render-Proxy, damit HTTPS und Client-IP korrekt erkannt werden |
| `CHALLENGE_YEAR` | `2026` |
| `CHALLENGE_MONTH` | `11` für November; `10` für einen Probelauf auf derselben Website |
| `ADMIN_PASSWORD` | Eigenes starkes Passwort, nur als geheime Render-Variable |
| `STRAVA_CLIENT_ID` | Bestehende Strava-App |
| `STRAVA_CLIENT_SECRET` | Geheimnis dieser App, nur im Backend |
| `STRAVA_REDIRECT_URI` | `https://api.novjogcha.ch/auth/callback` |
| `ENABLE_BACKGROUND_SYNC` | `1` |
| `ENABLE_DEBUG_ROUTES` | `0` |
| `LOAD_ENV_FILE` | `0` |
| `ALLOWED_ORIGINS` | Optional weitere vollständige Frontend-Ursprünge, durch Kommas getrennt |

Kein `ALLOW_SQLITE_FALLBACK` und keine geschätzte externe PostgreSQL-Adresse nötig. Eine falsche produktive Datenbankverbindung führt zu `/healthz` = 503, statt still eine leere lokale Datenbank anzulegen.

Docker-Konfiguration: Bei Repository-Root als Build Context den Root-`Dockerfile` verwenden; bei Root Directory `backend` den dortigen `Dockerfile`. Beide starten Uvicorn auf `0.0.0.0` und übernehmen Render-`PORT`. **Health Check Path: `/healthz`**. Siehe [Render Web Services](https://render.com/docs/web-services).

`FORWARDED_ALLOW_IPS=*` ist für den Betrieb hinter Render gedacht. Lokal bleibt der Uvicorn-Standard `127.0.0.1`; beim direkten öffentlichen Betrieb nur tatsächlich vertrauenswürdige Proxy-Adressen erlauben. Die korrekte Client-IP verhindert, dass die Begrenzung für Gast-Anfragen alle Teilnehmer gemeinsam trifft. [FastAPI hinter einem Proxy](https://fastapi.tiangolo.com/advanced/behind-a-proxy/).

Vor dem ersten produktiven Update einen aktuellen Datenbank-Backup/Snapshot erstellen. Beim Start läuft eine additive, versionierte Migration innerhalb einer Transaktion; PostgreSQL-Sperren schützen parallele Starts. Neue Tabellen speichern Wochenwertung, Sitzungen und Laufgruppen. Historische `users.slots`, `users.total_score`, Aktivitäten und `claims` bleiben erhalten. Manuell falsch gesetzte alte Strava-IDs müssen numerisch sein oder vorab korrigiert werden. Die Anwendung erzeugt keine neue verwaltete Datenbank.

## 3. Strava-App konfigurieren

In den Einstellungen der bestehenden Strava-App die **Authorization Callback Domain** auf `api.novjogcha.ch` setzen und die oben genannte Redirect-URI verwenden. Mit dem neuen Login bleibt die Website-Sitzung 90 Tage gültig und wird bei Nutzung in den letzten 30 Tagen verlängert. Cookies sind `Secure`, `HttpOnly`, `SameSite=Lax` und an den Backend-Host gebunden. Strava-Zugangstokens werden im Backend erneuert; sie sind nicht der Website-Login. Nach der Umstellung ist einmaliges erneutes Anmelden nötig. Browser, die Cookies löschen, benötigen weiterhin eine neue Anmeldung. Strava-Dokumentation: [OAuth und Token-Erneuerung](https://developers.strava.com/docs/authentication/).

## 4. Frontend konfigurieren

Im bestehenden Static-Site-Service:

| Einstellung | Wert |
| --- | --- |
| Root Directory | `frontend` |
| Build Command | `npm ci && npm run build` |
| Publish Directory | `dist` |
| `VITE_API_BASE_URL` | `https://api.novjogcha.ch` |
| `VITE_UI_PREVIEW` | `false` bzw. nicht setzen |

Die eingecheckte `.env.production` enthält ebenfalls diese API-Adresse. Eine eventuell bisher in Render gesetzte alte API-Adresse **überschreiben**, da Render-Variablen Vorrang haben. Nach Änderung neu bauen; Vite-Werte werden beim Build eingebettet.

Unter **Redirects/Rewrites** eine **Rewrite**-Regel setzen: Source `/*`, Destination `/index.html`, Action `Rewrite`. Dadurch funktionieren die direkten Aufrufe von `/admin`, `/about` (Über uns) und `/agb` (AGB & Datenschutz). Das vorhandene `_redirects` allein konfiguriert Render nicht. [Render Static Sites](https://render.com/docs/static-sites).

Optional anderer Kartenanbieter: `VITE_MAP_TILE_URL` mit `{z}/{x}/{y}` und passende `VITE_MAP_ATTRIBUTION`. Der Standard zeigt OpenStreetMap mit Quellenangabe. Für die Karte ist kein Strava-Login nötig.

## 5. Webhook optional aktualisieren

Der periodische vollständige Import läuft alle 30 Minuten und gleicht auch Änderungen/Löschungen ab. Für schnellere Aktualisierung Strava-Webhooks verwenden:

1. `STRAVA_WEBHOOK_VERIFY_TOKEN` im Backend als selbst gewähltes Geheimnis setzen.
2. Die vorhandene Subscription prüfen. Falls ihr Callback noch auf dem bisherigen Backend-Host liegt, diese nach der Strava-Anleitung auf `https://api.novjogcha.ch/auth/webhook` umstellen. Pro Strava-App ist nur eine Subscription möglich; bestehende nicht blind duplizieren.
3. Die zurückgegebene ID als `STRAVA_WEBHOOK_SUBSCRIPTION_ID` setzen. Ohne diese ID nimmt der POST-Endpunkt keine Ereignisse entgegen; der periodische Import bleibt aktiv.

GET-Verifikation liefert JSON mit `hub.challenge`. POST-Ereignisse werden zuerst bestätigt und danach im Hintergrund verarbeitet. Die Aktivität wird mit den echten Strava-Zugangsdaten geprüft. [Strava Webhooks](https://developers.strava.com/docs/webhooks/).

## 6. Nach dem Deployment prüfen

- `https://api.novjogcha.ch/healthz` meldet `ok`.
- Öffentliche Übersicht lädt ohne Anmeldung; Rangliste und Kilometerkurve sind konsistent.
- Strava-Anmeldung → persönliche Feldchen → Seite neu laden → weiterhin angemeldet. In einem zweiten Tab ebenfalls prüfen.
- `/admin` direkt aufrufen und anmelden; Abschlussdistanz setzen; Auslosung als Entwurf speichern. Öffentlich bleibt sie verborgen. Erst am gewünschten Tag veröffentlichen.
- Als Gast einen Lauf mit Kartenpunkt erstellen; in anderem Browser teilnehmen. Im ursprünglichen Browser bleiben Bearbeiten/Absagen nach Neuladen verfügbar.
- Auf Handy prüfen: drei Reiter, kompakte Rangliste, aufklappbare Details, Kartenpunkt und Formular.

Echte Strava-Autorisierung, Render-DNS/TLS und die produktive Migration lassen sich erst nach diesen Kontoeinstellungen abschliessend prüfen. Lokale Tests verändern diese Systeme nicht.
