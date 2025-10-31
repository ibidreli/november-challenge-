# backend/routes/admin.py
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from datetime import date
import os, uuid

from database import get_db
from models.user import User
from models.activity import Activity

router = APIRouter()

# --- simpler Header-Auth-Guard ---
def require_admin(x_admin_secret: str | None = Header(None, alias="X-Admin-Secret")):
    expected = os.getenv("ADMIN_SECRET", "")
    if not expected or x_admin_secret != expected:
        raise HTTPException(status_code=403, detail="Unauthorized (invalid X-Admin-Secret)")

# ---------- USERS ----------
@router.get("/users", dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id.asc()).all()
    return [{"id": u.id, "name": u.name, "strava_id": u.strava_id, "total_score": float(u.total_score or 0)} for u in users]

@router.post("/users", dependencies=[Depends(require_admin)])
def create_user(name: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    u = User(name=name.strip(), strava_id=None)
    db.add(u); db.commit(); db.refresh(u)
    return {"id": u.id, "name": u.name}

# ---------- ACTIVITIES ----------
@router.get("/activities", dependencies=[Depends(require_admin)])
def list_activities(
    db: Session = Depends(get_db),
    user_id: int | None = None,
    y: int | None = None,
    m: int | None = None,
    limit: int = 200,
    offset: int = 0
):
    q = db.query(Activity)
    if user_id: q = q.filter(Activity.user_id == user_id)
    if y and m:
        q = q.filter(Activity.date >= date(y, m, 1))
        q = q.filter(Activity.date < date(y + (1 if m == 12 else 0), (1 if m == 12 else m + 1), 1))
    total = q.count()
    items = (q.order_by(Activity.date.desc(), Activity.id.desc()).offset(offset).limit(limit).all())
    return {
        "total": total,
        "items": [{
            "id": a.id,
            "user_id": a.user_id,
            "strava_id": a.strava_id,
            "date": a.date.isoformat() if a.date else None,
            "distance_km": float(a.distance_km or 0),
            "status": a.status
        } for a in items]
    }

@router.post("/activities", dependencies=[Depends(require_admin)])
def create_activity(
    user_id: int,
    distance_km: float,
    date_str: str | None = None,
    db: Session = Depends(get_db),
):
    if distance_km <= 0:
        raise HTTPException(status_code=400, detail="distance_km must be > 0")
    u = db.query(User).get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    d = date.today()
    if date_str:
        try:
            d = date.fromisoformat(date_str)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date (YYYY-MM-DD)")

    manual_id = f"manual:{uuid.uuid4().hex[:16]}"
    a = Activity(user_id=u.id, strava_id=manual_id, date=d, distance_km=distance_km, status="fetched")
    db.add(a); db.commit(); db.refresh(a)

    # vorhandene Bewertungs-/Slot-Logik optional anwenden
    try:
        from routes.activities import process_activity_instance  # gleicher Ordner -> funktioniert
        process_activity_instance(a, db)
    except Exception:
        pass

    return {"id": a.id}

@router.put("/activities/{activity_id}", dependencies=[Depends(require_admin)])
def update_activity(
    activity_id: int,
    user_id: int | None = None,
    distance_km: float | None = None,
    date_str: str | None = None,
    db: Session = Depends(get_db),
):
    a = db.query(Activity).get(activity_id)
    if not a:
        raise HTTPException(status_code=404, detail="Activity not found")

    if user_id is not None:
        u = db.query(User).get(user_id)
        if not u:
            raise HTTPException(status_code=404, detail="User not found")
        a.user_id = user_id

    if distance_km is not None:
        if distance_km <= 0:
            raise HTTPException(status_code=400, detail="distance_km must be > 0")
        a.distance_km = distance_km

    if date_str is not None:
        try:
            a.date = date.fromisoformat(date_str)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date (YYYY-MM-DD)")

    db.add(a); db.commit(); db.refresh(a)

    try:
        from routes.activities import process_activity_instance
        process_activity_instance(a, db)
    except Exception:
        pass

    return {"ok": True}

@router.delete("/activities/{activity_id}", dependencies=[Depends(require_admin)])
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    a = db.query(Activity).get(activity_id)
    if not a:
        raise HTTPException(status_code=404, detail="Activity not found")
    db.delete(a); db.commit()
    return {"ok": True}
