# Lokaler Entwicklungsworkflow

## 1. UI-Preview ohne Backend

Dieser Modus ist fuer Layout- und CSS-Arbeit gedacht. Er verwendet stabile Beispieldaten und macht keine API-Requests.

```powershell
Set-Location frontend
npm run dev:ui
```

Danach `http://localhost:5173` im Browser oeffnen. Aenderungen an React- und CSS-Dateien werden per Vite-HMR direkt sichtbar.

Die Admin-Ansicht ist unter `http://localhost:5173/admin` erreichbar. Sie startet im Preview-Modus automatisch angemeldet und verwendet ebenfalls lokale Beispieldaten.

## 2. Lokaler Full-Stack

Die Datenbank und das Backend koennen mit Docker gestartet werden:

```powershell
docker compose up db backend
```

In einem zweiten Terminal wird das Frontend gestartet:

```powershell
Set-Location frontend
npm run dev:local
```

Das Frontend nutzt standardmaessig relative API-Requests. Vite leitet `/auth`, `/users`, `/activities` und `/admin` an `http://localhost:8000` weiter.

Pruefen:

- API: `http://localhost:8000/healthz`
- Frontend: `http://localhost:5173`
- Diagnose bei fehlgeschlagenem Backend-Start: `http://localhost:8000/debug/nodb`

Strava-OAuth ist fuer diesen Workflow optional. Ohne lokale Strava-Konfiguration bleiben Login und Synchronisation deaktiviert, die UI und die lokalen Datenbankrouten koennen trotzdem entwickelt werden.

## 3. Explizite externe API

Eine externe API wird nur noch bewusst aktiviert. In PowerShell:

```powershell
$env:VITE_API_BASE_URL = "https://november-challenge.onrender.com"
npm run dev
```

Alternativ kann eine API-Basis einmalig ueber `?backend_base=https://...` gesetzt werden. Ohne diese Konfiguration verwendet das Frontend immer den lokalen Vite-Proxy.

## Nuetzliche Befehle

```powershell
Set-Location frontend
npm run build
npm run preview
npm run preview:ui
```

`npm run preview` zeigt den zuletzt gebauten Produktions-Build. `npm run preview:ui` baut zuerst mit dem UI-Modus und zeigt danach den UI-Preview-Build mit Beispieldaten.

## Troubleshooting

- `ECONNREFUSED localhost:8000`: Backend oder Docker-Service laeuft nicht.
- UI bleibt bei alten Daten: Browser hart neu laden oder pruefen, ob versehentlich `dev:ui` aktiv ist.
- Falsche API sichtbar: Browser-Konsole auf `API Base URL set to ...` pruefen. Im lokalen Modus muss dort `same-origin (Vite proxy)` stehen.
- Port 5173 belegt: Prozess beenden; der Vite-Server verwendet absichtlich `strictPort`, damit nicht unbemerkt eine andere URL entsteht.
