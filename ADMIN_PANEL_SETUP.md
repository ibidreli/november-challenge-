# Admin Panel Setup Guide

## 🎯 Overview

Das neue Admin-Panel ermöglicht dir folgende Funktionen:
- **Spieler verwalten**: Hinzufügen, Bearbeiten, Löschen
- **Aktivitäten verwalten**: Manuelle Aktivitäten pro Spieler hinzufügen/bearbeiten/löschen
- **Gewichtung**: Manuelle Einträge haben Priorität vor Strava-Daten (werden nicht überschrieben)

## 🔐 Passwort setzen

Um das Admin-Panel zu schützen, setze die Environment-Variable `ADMIN_PASSWORD`:

### In Render:
1. Gehe zu deinem Backend-Service in Render
2. Klicke auf "Environment"
3. Füge diese Variable hinzu:
   ```
   ADMIN_PASSWORD=your_secure_password_here
   ```
4. Speichern und der Service wird automatisch neu gestartet

### Lokal (.env Datei):
```bash
ADMIN_PASSWORD=your_secure_password_here
```

## 🚀 Zugang zum Admin-Panel

1. **URL öffnen**: `https://deine-domain.com/admin`
   - Oder lokal: `http://localhost:5173/admin`

2. **Passwort eingeben**: Das Passwort, das du oben gesetzt hast

3. **Login**: Du wirst automatisch angemeldet und erhältst einen Token (2 Stunden gültig)

## 📋 Funktionen

### Tab "Users" (Spieler)

**Spieler hinzufügen:**
- Gib einen Namen ein
- Klick "Add Player"

**Spieler ansehen:**
- Alle Spieler werden als Karten angezeigt
- Score: Gesamtpunkte des Spielers
- Total KM: Summe aller KM aus den Slots

**Aktionen:**
- **Edit Activities**: Öffne das Activities-Tab, um Aktivitäten zu bearbeiten
- **Reset**: Setze alle Slots und Score auf 0 zurück
- **Delete**: Lösche Spieler und alle seine Daten

### Tab "Activities" (Aktivitäten)

**Spieler wählen:**
- Klick auf einen Spieler, um seine Aktivitäten zu bearbeiten

**Aktivität hinzufügen:**
- **Date**: Datum der Aktivität (Format: YYYY-MM-DD)
- **Distance (km)**: Distanz in Kilometern (mit Dezimal)
- Klick "Add Activity"

**Aktivitäten ansehen:**
- **Date**: Datum der Aktivität
- **Distance (km)**: Eingabe-Distanz
- **Effective KM**: Wie viele KM tatsächlich zugewiesen wurden (in den Slots)
- **Type**: "Manual" (von dir) oder "Strava" (von Strava)
- **Status**: "pending", "claimed", etc.

**Aktivitäten löschen:**
- Nur manuelle Aktivitäten können gelöscht werden
- Strava-Aktivitäten sind read-only

## 🔄 Wie Strava-Integration funktioniert

### Automatische Synchronisation:
1. Beim Dashboard-Laden wird `POST /users/sync_all` aufgerufen
2. Das Backend holt die neuesten Aktivitäten von Strava
3. Diese werden als "Strava" Aktivitäten gespeichert

### Priorität: Manuelle Einträge gewinnen
- **Wenn eine manuelle Aktivität für einen Tag existiert:**
  - Strava-Aktivitäten für diesen Tag werden NICHT importiert
  - Die manuelle Aktivität behält die Kontrolle
  
- **Wenn keine manuelle Aktivität existiert:**
  - Strava-Aktivitäten werden normal verarbeitet

### Beispiel:
```
Spieler: Max
- 15.11.2024: 10 km von Strava → wird importiert
- 16.11.2024: Manuelle 12 km hinzugefügt
  - Auch wenn Strava 15 km zeigt → wird ignoriert!
  - Max's 12 km bleiben bestehen
```

## 🔧 Technische Details

### Backend Changes:

1. **Activity-Modell** (`backend/models/activity.py`):
   - Neue Spalte: `is_manual` (Boolean)
   - `False` = von Strava, `True` = Manuelle Eingabe

2. **Admin Routes** (`backend/routes/admin.py`):
   - `POST /admin/login` - Authentifizierung
   - `GET/POST /admin/users` - Spieler verwalten
   - `GET/POST /admin/users/{user_id}/activities` - Aktivitäten verwalten
   - Token-basiert mit 2-Stunden Expiry

3. **Strava Sync** (`backend/auth/routes.py`):
   - Prüft vor dem Import, ob eine manuelle Aktivität existiert
   - Wenn ja → überspringt Strava-Import für diesen Tag

4. **Database Migrations**:
   - `is_manual` Spalte wird automatisch hinzugefügt
   - Funktioniert mit PostgreSQL und SQLite

### Frontend Changes:

1. **AdminPanel Komponente** (`frontend/src/components/AdminPanel.jsx`):
   - Login-Seite mit Passwort
   - Zwei Tabs: Users & Activities
   - Modernes, responsives Design

2. **App.jsx**:
   - Erkennt `/admin` URL
   - Zeigt AdminPanel statt Dashboard an

3. **vite.config.js**:
   - `/admin` Proxy zum Backend konfiguriert

## 🛡️ Sicherheit

- **Passwort-Schutz**: Alle Admin-Endpoints erfordern `ADMIN_PASSWORD`
- **Token-basiert**: Nach Login erhältst du einen Token (2 Stunden gültig)
- **Keine Persistierung**: Token wird nur im Browser gespeichert (localStorage)
- **Logout**: Token wird auf dem Server invalidiert

## 📝 Beispiel-Workflows

### Workflow 1: Spieler hinzufügen
1. Login ins Admin-Panel
2. Tab "Users" → "Add New Player"
3. Namen eingeben → "Add Player"
4. Spieler erscheint in der Liste

### Workflow 2: Aktivität manuell hinzufügen
1. Login ins Admin-Panel
2. Tab "Activities"
3. Spieler wählen
4. Date & Distance eingeben
5. "Add Activity"
6. Aktivität wird in der Tabelle angezeigt

### Workflow 3: Falsche Aktivität löschen
1. Tab "Activities"
2. Spieler wählen
3. Aktivität in der Tabelle finden
4. "Delete" Button klicken
5. Bestätigen → gelöscht

### Workflow 4: Reset für neuen Monat
1. Tab "Users"
2. Spieler-Karte → "Reset" Button
3. Bestätigen
4. Alle Slots & Score werden auf 0 zurückgesetzt

## 🐛 Troubleshooting

**Problem**: "Admin token required" Fehler
- **Lösung**: Überprüfe, dass `ADMIN_PASSWORD` in Render Env gesetzt ist

**Problem**: Strava-Aktivitäten überschreiben manuelle Einträge
- **Lösung**: Das sollte nicht passieren. Stelle sicher, dass:
  - Backend neu deployed ist
  - `is_manual` Spalte in der Datenbank existiert
  - Falls nötig, alte Aktivitäten löschen und neu hinzufügen

**Problem**: Login funktioniert nicht
- **Lösung**: 
  - Token abgelaufen? → Page neu laden
  - Falsches Passwort? → Überprüfe `ADMIN_PASSWORD` in Render Env

## 📞 Support

Wenn etwas nicht funktioniert:
1. Schau in die Backend-Logs (Render Dashboard → Logs)
2. Überprüfe, dass alle Environment-Variablen gesetzt sind
3. Stelle sicher, dass der Frontend und Backend neu deployed sind

---

Happy managing! 🎉
