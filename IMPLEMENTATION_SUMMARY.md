# Admin Panel Implementation Summary

## ✅ Was wurde implementiert?

### 🎯 Hauptfunktionen

1. **Admin-Zugang**: `/admin` Route mit Passwort-Schutz
2. **Spieler-Management**: Spieler hinzufügen/bearbeiten/löschen
3. **Aktivitäts-Management**: Manuelle Aktivitäten pro Spieler verwalten
4. **Prioritätssystem**: Manuelle Einträge überschreiben NICHT Strava-Daten

---

## 📦 Backend-Änderungen

### 1. Modelle (`backend/models/`)

**activity.py**:
- ✅ Neue Spalte: `is_manual: Boolean` (default: False)
- Unterscheidung zwischen manuellen und Strava-Aktivitäten

### 2. Neue Routes (`backend/routes/admin.py`)

Komplette Admin-API mit Authentifizierung:

```python
# Authentication
POST /admin/login - Passwort-Login (gibt Token zurück)
POST /admin/logout - Logout

# User Management
GET /admin/users - Alle Spieler
POST /admin/users - Neuen Spieler erstellen
PUT /admin/users/{user_id} - Spieler aktualisieren
DELETE /admin/users/{user_id} - Spieler löschen

# Activity Management
GET /admin/users/{user_id}/activities - Aktivitäten eines Spielers
POST /admin/users/{user_id}/activities - Neue Aktivität erstellen
PUT /admin/users/{user_id}/activities/{activity_id} - Aktivität bearbeiten
DELETE /admin/users/{user_id}/activities/{activity_id} - Aktivität löschen

# Utilities
POST /admin/users/{user_id}/reset-slots - Reset Score & Slots
```

### 3. Strava-Sync-Logik (`backend/auth/routes.py`)

Geändert in `sync_recent_activities_from_strava()`:
- ✅ Prüft vor Import: Existiert manuelle Aktivität für diesen Tag?
- ✅ Wenn ja: Überspringt Strava-Import (manuelle Einträge gewinnen)
- ✅ Wenn nein: Importiert Strava-Aktivität normal

```python
# Neue Logik:
manual_exists = db.query(Activity).filter(
    Activity.user_id == user.id,
    Activity.date == act_date,
    Activity.is_manual == True
).first()
if manual_exists:
    logging.info("Skipping Strava activity (manual entry exists)")
    continue
```

### 4. Database-Migrationen (`backend/database.py`)

Neue Migration-Funktion:
- ✅ `ensure_is_manual_column()` - Fügt `is_manual` Spalte automatisch hinzu
- ✅ PostgreSQL & SQLite Support
- ✅ Lädt beim Startup automatisch

### 5. Main Entry Point (`backend/main.py`)

- ✅ Importiert neue `admin_router`
- ✅ Registriert `/admin` Prefix
- ✅ Ruft `ensure_is_manual_column()` beim Startup auf

---

## 🎨 Frontend-Änderungen

### 1. Neue Komponente (`frontend/src/components/AdminPanel.jsx`)

Komplettes Admin-Interface mit:
- ✅ Login-Bildschirm (Passwort-Input)
- ✅ Token-Verwaltung (localStorage)
- ✅ Zwei Tabs: Users & Activities
- ✅ Responsives Design
- ✅ Error/Success Messages

**Features**:
- Spieler-Karten mit Score/KM-Anzeige
- Formulare für Add/Edit/Delete
- Aktivitäts-Tabelle mit Sortierung
- Unterscheidung: Manual vs. Strava

### 2. AdminPanel CSS (`frontend/src/components/AdminPanel.css`)

- ✅ Modern, Clean Design
- ✅ Responsive für Mobile/Desktop
- ✅ Login-Seite mit Gradient
- ✅ Farbcodierung: Green (Add), Blue (Edit), Red (Delete), Yellow (Reset)

### 3. App.jsx

- ✅ Erkennt `/admin` URL automatisch
- ✅ Zeigt AdminPanel statt Dashboard an
- ✅ Pausiert Strava-Sync im Admin-Modus

### 4. vite.config.js

- ✅ Proxy für `/admin` Endpoints hinzugefügt

---

## 🔐 Sicherheit

### Authentifizierung
- ✅ Passwort-basiert (`ADMIN_PASSWORD` Environment-Var)
- ✅ Token-basiert nach Login (2 Stunden gültig)
- ✅ Token wird in localStorage gespeichert
- ✅ Custom Header: `X-Admin-Token`

### Autorisierung
- ✅ Alle Admin-Endpoints erfordern gültigen Token
- ✅ Token-Expiry wird bei jedem Request erneuert
- ✅ Logout invalidiert Token auf Server-Seite

### Datenschutz
- ✅ Manuelle Aktivitäten können nicht von Strava überschrieben werden
- ✅ Alle Änderungen bleiben persistent
- ✅ Reset-Funktion zur Datenbereinigung

---

## 🚀 Deployment-Checklist

### Vor dem Deploy:

1. **Backend**:
   - ✅ `ensure_is_manual_column()` ist in main.py aufgerufen
   - ✅ `admin_router` ist registriert
   - ✅ Strava-Sync-Logik aktualisiert

2. **Frontend**:
   - ✅ `AdminPanel.jsx` & `AdminPanel.css` vorhanden
   - ✅ `App.jsx` angepasst
   - ✅ `vite.config.js` mit `/admin` Proxy

3. **Environment**:
   - ✅ `ADMIN_PASSWORD` in Render Env gesetzt

### Nach dem Deploy:

1. Testen: `https://deine-domain.com/admin`
2. Mit Passwort anmelden
3. Spieler hinzufügen & testen
4. Aktivitäten hinzufügen & testen
5. Strava-Sync testen (sollte manuelle Einträge nicht überschreiben)

---

## 📊 Datenbankänderungen

### Neue Spalten:

**activities Tabelle**:
```sql
-- PostgreSQL
ALTER TABLE activities ADD COLUMN is_manual BOOLEAN DEFAULT FALSE;

-- SQLite
ALTER TABLE activities ADD COLUMN is_manual INTEGER DEFAULT 0;
```

**Automatische Migration**: 
- Lädt beim Backend-Start
- Kein manuelles Eingreifen nötig
- Existierende Daten: `is_manual = FALSE` (Strava-Standard)

---

## 🎯 Workflow-Beispiele

### Beispiel 1: Neuer Spieler
```
1. Admin-Panel öffnen → /admin
2. Password eingeben
3. Tab "Users" → "Add New Player"
4. Name: "Max" → Add
5. Max erscheint in der Liste
```

### Beispiel 2: Manuelle Aktivität
```
1. Tab "Activities"
2. Spieler "Max" wählen
3. Date: 2024-11-15
4. Distance: 12.5 km
5. Add Activity
6. ✅ Manuelle Aktivität wird gespeichert
7. Strava kann diesen Tag nicht mehr überschreiben!
```

### Beispiel 3: Falsches Ergebnis korrigieren
```
1. Tab "Activities"
2. Spieler wählen
3. Aktivität finden → Delete
4. Alte Slots/Score werden rückgängig gemacht
5. Neue Aktivität hinzufügen mit korrekten Werten
```

---

## 🔧 Technische Details

### Token-System
```javascript
// Login
POST /admin/login?password=XYZ
Response: { token: "...", expires_in: 7200 }

// Nachfolgende Requests
Header: X-Admin-Token: <token>

// Token wird erneuert: +2 Stunden bei jedem Request
// Token verfällt nach 2 Stunden ohne Aktivität
```

### Manuelle vs. Strava
```python
# Beim Strava-Import:
if Activity.filter(
    user_id=user.id, 
    date=act_date, 
    is_manual=True
).exists():
    # Überspringe Strava-Import
    continue
else:
    # Normaler Import mit is_manual=False
    create_activity(..., is_manual=False)
```

### Slots-Management
```python
# Beim Activity-Delete:
1. Suche Claim für Activity
2. Undo Score: total_score -= claim.km
3. Clear Slot: slots[idx] = None
4. Delete Claim & Activity
```

---

## 📝 Konfiguration

### Environment-Variablen (Render)

```
# Passwort für Admin-Panel (ERFORDERLICH!)
ADMIN_PASSWORD=super_secure_password_123

# Automatisch beim Start:
# - Activity.is_manual Spalte wird erstellt
# - Migrations laufen automatisch
```

### Optional (nur lokal)

```
# .env Datei
ADMIN_PASSWORD=dev_password
CHALLENGE_MONTH=11
DATABASE_URL=postgresql://...
```

---

## ✨ Besonderheiten

1. **Automatische Migrations**: Keine SQL-Befehle nötig
2. **Token-Expiry**: Automatische Sicherheit nach 2 Stunden
3. **Responsive Design**: Funktioniert auf Mobile & Desktop
4. **Fehlerbehandlung**: Klare Error-Messages
5. **Prioritätssystem**: Manuelle Einträge gewinnen immer
6. **Umfassende Logs**: Alle Actionen werden geloggt

---

## 🐛 Häufige Fehler & Lösungen

| Problem | Ursache | Lösung |
|---------|--------|--------|
| "Admin token required" | ADMIN_PASSWORD nicht gesetzt | `ADMIN_PASSWORD` in Render Env hinzufügen |
| Login fehlgeschlagen | Falsches Passwort | Richtes Passwort aus Env verwenden |
| Strava überschreibt manuelle | Alte Backend-Version | Frontend & Backend neu deployen |
| Token abgelaufen | Nach 2 Stunden | Seite neu laden |
| Spalte existiert nicht | Vor Migration | Backend redeploy → Migration lädt automatisch |

---

## 🎉 Fertig!

Das Admin-Panel ist komplett implementiert und einsatzbereit. Alle Anforderungen wurden erfüllt:

✅ Admin-Zugang unter `/admin`  
✅ Passwort-Schutz  
✅ Spieler-Management  
✅ Aktivitäts-Management  
✅ Manuelle Einträge haben Priorität  
✅ Frontend & Backend Integration  
✅ Automatische Migrations  
✅ Responsive Design  

Viel Erfolg! 🚀
