from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import os, time, uuid, logging

from database import get_db
from models.user import User
from models.activity import Activity
from models.claim import Claim
from sqlalchemy.orm.attributes import flag_modified

router = APIRouter()

# simple in-memory admin session store: token -> expires_epoch
ADMIN_SESSIONS: dict = {}
# token TTL seconds
ADMIN_TTL = int(os.getenv("ADMIN_TOKEN_TTL", "3600"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

def _require_admin(request: Request):
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Admin interface disabled (no ADMIN_PASSWORD set).")
    token = request.headers.get("x-admin-token") or ""
    if not token and request.headers.get("authorization", ""):
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing admin token")
    entry = ADMIN_SESSIONS.get(token)
    if not entry or entry < time.time():
        # remove expired if present
        if token in ADMIN_SESSIONS:
            ADMIN_SESSIONS.pop(token, None)
        raise HTTPException(status_code=401, detail="Invalid or expired admin token")
    return token

@router.post("/login")
def admin_login(payload: dict):
    """
    Body: {"password": "<pw>"}
    Returns: {"token": "...", "expires": epoch}
    """
    if not ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Admin interface disabled")
    pw = payload.get("password") if isinstance(payload, dict) else None
    if not pw or pw != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = uuid.uuid4().hex
    expires = time.time() + ADMIN_TTL
    ADMIN_SESSIONS[token] = expires
    return {"token": token, "expires": expires}

# Players
@router.get("/players")
def list_players(db: Session = Depends(get_db), _=Depends(_require_admin)):
    users = db.query(User).all()
    out = []
    for u in users:
        try:
            u.ensure_slots()
        except Exception:
            pass
        out.append({"id": u.id, "name": u.name, "strava_id": u.strava_id, "total_score": int(u.total_score or 0), "slots": u.slots})
    return out

@router.post("/player")
def create_player(payload: dict, db: Session = Depends(get_db), _=Depends(_require_admin)):
    name = payload.get("name")
    strava_id = payload.get("strava_id")
    if not name:
        raise HTTPException(status_code=400, detail="name required")
    # avoid duplicate strava_id
    if strava_id:
        exists = db.query(User).filter_by(strava_id=strava_id).first()
        if exists:
            raise HTTPException(status_code=400, detail="user with strava_id exists")
    user = User(name=name, strava_id=(int(strava_id) if strava_id else None))
    try:
        user.ensure_slots()
    except Exception:
        pass
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name, "strava_id": user.strava_id}

@router.delete("/player/{user_id}")
def delete_player(user_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    # delete related claims and activities first
    try:
        db.query(Claim).filter(Claim.user_id == user.id).delete(synchronize_session=False)
        db.query(Activity).filter(Activity.user_id == user.id).delete(synchronize_session=False)
        db.delete(user)
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        logging.exception("delete_player failed")
        raise HTTPException(status_code=500, detail=str(e))

# Activities (admin-created manual activities are stored with status 'manual')
@router.post("/activity")
def add_activity(payload: dict, db: Session = Depends(get_db), _=Depends(_require_admin)):
    """
    payload: { "user_id": int OR "strava_id": int, "date": "YYYY-MM-DD", "km": number }
    """
    user = None
    if "user_id" in payload:
        user = db.query(User).filter(User.id == int(payload["user_id"])).first()
    elif "strava_id" in payload:
        user = db.query(User).filter(User.strava_id == int(payload["strava_id"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    date_s = payload.get("date")
    km = payload.get("km")
    if not date_s or km is None:
        raise HTTPException(status_code=400, detail="date and km required")
    try:
        dt = __import__("datetime").datetime.fromisoformat(date_s).date()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid date format, use YYYY-MM-DD")
    try:
        activity = Activity(user_id=user.id, strava_id=f"manual-{uuid.uuid4().hex}", date=dt, distance_km=float(km), status="manual")
        db.add(activity)
        db.commit()
        db.refresh(activity)
        # assign to user's slots using existing helper
        assigned = user.assign_activity(int(float(km)), activity.id)
        if assigned:
            claim = Claim(user_id=user.id, km=assigned, date=dt, activity_id=activity.id)
            try:
                flag_modified(user, "slots")
            except Exception:
                pass
            db.add(claim)
            db.add(user)
            activity.effective_km = assigned
            activity.status = "claimed"
            db.add(activity)
            db.commit()
            return {"ok": True, "activity_id": activity.id, "assigned_km": assigned}
        else:
            db.commit()
            return {"ok": True, "activity_id": activity.id, "assigned_km": None}
    except Exception as e:
        db.rollback()
        logging.exception("add_activity failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/activity/{activity_id}")
def delete_activity(activity_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="activity not found")
    try:
        user = db.query(User).filter(User.id == activity.user_id).first() if activity.user_id else None
        # remove claim row(s)
        db.query(Claim).filter(Claim.activity_id == activity.id).delete(synchronize_session=False)
        # if the activity had been assigned to a slot, clear it and adjust total_score
        if user:
            try:
                user.ensure_slots()
                modified = False
                slots = list(user.slots or [])
                for i, s in enumerate(slots):
                    if isinstance(s, dict) and s.get("activity_id") == activity.id:
                        km = int(s.get("km") or 0)
                        slots[i] = None
                        user.slots = slots
                        try:
                            user.total_score = max(0, int(user.total_score or 0) - km)
                        except Exception:
                            pass
                        try:
                            flag_modified(user, "slots")
                        except Exception:
                            pass
                        modified = True
                        break
                if modified:
                    db.add(user)
            except Exception:
                db.rollback()
                logging.exception("failed to remove slot reference")
        # finally delete activity
        db.delete(activity)
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        logging.exception("delete_activity failed")
        raise HTTPException(status_code=500, detail=str(e))
