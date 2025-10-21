from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from models.activity import Activity
from models.claim import Claim
from models.user import User
from database import get_db
import datetime
import requests
import os

router = APIRouter()

# new: configure challenge month via env (default 11 = November)
CHALLENGE_MONTH = int(os.getenv("CHALLENGE_MONTH", "11"))


# new helper: process an Activity instance (reusable)
def process_activity_instance(activity: Activity, db: Session, simulate_month: int | None = None):
    """
    Process an Activity SQLAlchemy instance and create a Claim if possible.
    Returns dict with result (same shape as endpoint responses).
    """
    if not activity:
        raise ValueError("activity is None")
    if not activity.user_id:
        return {"error": "Activity has no associated user"}
    user = db.query(User).filter(User.id == activity.user_id).first()
    if not user:
        return {"error": "User not found"}

    act_date = activity.date
    if not isinstance(act_date, datetime.date):
        return {"error": "Activity date invalid"}

    # Only one claim per user per day
    existing_claim = db.query(Claim).filter(Claim.user_id == user.id, Claim.date == act_date).first()
    if existing_claim:
        return {"message": "User already has a claim for this date", "claim": {"km": existing_claim.km}}

    # Determine month to use (env override or simulate param)
    month_to_check = simulate_month if simulate_month is not None else CHALLENGE_MONTH

    if month_to_check != act_date.month:
        return {"message": "Activity is outside challenge month; ignored for challenge.", "month_checked": month_to_check}

    day = act_date.day
    max_allowed = 30 if day == 30 else 29
    # floor distance
    if activity.distance_km is None:
        return {"error": "Activity distance missing"}
    floor_km = int(activity.distance_km // 1)
    candidate_start = min(floor_km, max_allowed)

    # use assign_activity to pick the best available slot <= candidate_start
    assigned = user.assign_activity(candidate_start, activity.id)
    if assigned:
        # create claim and persist changes (user.slots and user.total_score already updated)
        claim = Claim(user_id=user.id, km=assigned, date=act_date, activity_id=activity.id)
        db.add(claim)
        activity.status = "claimed"
        activity.effective_km = assigned
        # ensure SQLAlchemy sees slots change (assign_activity already flagged, but be safe)
        try:
            flag_modified(user, "slots")
        except Exception:
            pass
        db.add(user)
        db.add(activity)
        db.commit()
        db.refresh(claim)
        return {"message": "Claim created", "km": assigned}
    return {"message": "No available km to claim for this activity"}


@router.get("/")
def get_all_activities(db: Session = Depends(get_db)):
    return db.query(Activity).all()


@router.post("/process/{activity_id}")
def process_activity(activity_id: int, simulate_november: bool = False, db: Session = Depends(get_db)):
    """
    Process a stored Activity. Optional query param simulate_november=True treats the activity
    as if it were in November (useful for local testing in other months).
    """
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # use simulate flag to override month for testing
    simulate_month = 11 if simulate_november else None
    result = process_activity_instance(activity, db, simulate_month=simulate_month)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# New endpoint: fetch activity from Strava (by strava activity id), store and process it.
@router.post("/process_by_strava/{strava_activity_id}")
def process_by_strava(strava_activity_id: int, owner_strava_id: int | None = None, simulate_november: bool = False, db: Session = Depends(get_db)):
    """
    If the activity exists in DB -> process it.
    Otherwise: find a matching user (owner_strava_id or first user), fetch activity from Strava,
    insert Activity row and call process_activity(...) to apply claim logic.
    """
    # look for existing activity by strava_id
    existing = db.query(Activity).filter(Activity.strava_id == str(strava_activity_id)).first()
    if existing:
        return process_activity(existing.id, simulate_november, db)

    # find user: by owner_strava_id if given, otherwise try to use first user
    user = None
    if owner_strava_id is not None:
        user = db.query(User).filter(User.strava_id == owner_strava_id).first()
    else:
        user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found (provide owner_strava_id if multiple users exist)")

    if not user.access_token:
        return {"status": "no_token", "message": "User has no access_token"}

    # fetch activity from Strava
    STRAVA_API_BASE = "https://www.strava.com/api/v3/activities/"
    try:
        headers = {"Authorization": f"Bearer {user.access_token}"}
        r = requests.get(f"{STRAVA_API_BASE}{strava_activity_id}", headers=headers, timeout=10)
        if r.status_code != 200:
            return {"status": "error_fetching_activity", "code": r.status_code, "text": r.text}
        data = r.json()
        # ignore non-Run activities
        if (data.get("type") or "").lower() != "run":
            return {"status": "ignored_non_run", "type": data.get("type")}
        distance_m = data.get("distance", 0) or 0
        distance_km = float(distance_m) / 1000.0
        start = data.get("start_date_local") or data.get("start_date")
        if not start:
            raise ValueError("activity missing start_date")
        # parse ISO date/time -> date
        # strip trailing Z if present
        if start.endswith("Z"):
            start = start[:-1]
        dt = datetime.datetime.fromisoformat(start)
        act_date = dt.date()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch/parse Strava activity: {e}")

    # create Activity in DB
    try:
        activity = Activity(user_id=user.id, strava_id=str(strava_activity_id), date=act_date, distance_km=distance_km, status="fetched")
        db.add(activity)
        db.commit()
        db.refresh(activity)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to insert Activity: {e}")

    # process newly created activity via helper
    simulate_month = 11 if simulate_november else None
    result = process_activity_instance(activity, db, simulate_month=simulate_month)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result