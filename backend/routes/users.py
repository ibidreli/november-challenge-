from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from models.user import User
from database import get_db


router = APIRouter()


@router.get("/me")
def get_current_user(sync: bool = Query(False), db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        return {"message": "No users found."}
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