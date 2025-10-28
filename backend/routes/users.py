from fastapi import APIRouter, Depends, Query, Header, HTTPException
from sqlalchemy.orm import Session
from models.user import User
from database import get_db
from typing import Optional


router = APIRouter()


@router.get("/me")
def get_current_user(sync: bool = Query(False), auth_header: Optional[str] = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """
    Require Authorization: Bearer <access_token>.
    If no valid token provided, return 401 so frontend shows login screen.
    """
    # extract bearer token
    if not auth_header:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter_by(access_token=token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # optionally sync only this user (useful for frontend to refresh current user's activities)
    if sync:
        try:
            # import locally to avoid circular import at module import time
            from auth.routes import sync_recent_activities_from_strava
            sync_result = sync_recent_activities_from_strava(user, db)
            # ignore/surface result as needed
        except Exception:
            pass
    user.ensure_slots()
    return {
        "id": user.id,
        "name": user.name,
        "strava_id": user.strava_id,
        "total_score": user.total_score,
        "slots": user.slots
    }


@router.post("/sync_all")
def sync_all_users(db: Session = Depends(get_db)):
    """
    Trigger sync for all users (fetch activities from Strava since CHALLENGE_MONTH start).
    Frontend can call this on page load to ensure newest activities appear without re-auth.
    """
    users = db.query(User).all()
    summary = []
    try:
        from auth.routes import sync_recent_activities_from_strava
    except Exception:
        from backend.auth.routes import sync_recent_activities_from_strava

    for u in users:
        try:
            res = sync_recent_activities_from_strava(u, db)
            summary.append({"user_id": u.id, "strava_id": u.strava_id, "result": res})
        except Exception as e:
            summary.append({"user_id": u.id, "strava_id": u.strava_id, "error": str(e)})
    return {"synced": len(summary), "details": summary}


# New: simple listing endpoint for leaderboard
@router.get("/")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    out = []
    for u in users:
        try:
            u.ensure_slots()
        except Exception:
            pass
        km_total = 0
        slots_out = []
        for s in (u.slots or []):
            # normalize slot representation: either null or integer km
            if isinstance(s, dict) and "km" in s and isinstance(s["km"], (int, float)):
                km_val = int(s["km"])
                km_total += km_val
                slots_out.append(km_val)
            else:
                slots_out.append(None)
        out.append({
            "id": u.id,
            "name": u.name,
            "total_score": u.total_score or 0,
            "km_total": km_total,
            "slots": slots_out   # add slots for frontend mini-grid
        })
    # sort by score desc, fallback to km_total
    out.sort(key=lambda x: (x["total_score"], x["km_total"]), reverse=True)
    return out