from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.activity import Activity
from models.claim import Claim
from models.user import User
from database import get_db
import datetime
import requests

router = APIRouter()


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

    if not activity.user_id:
        raise HTTPException(status_code=400, detail="Activity has no associated user")

    user = db.query(User).filter(User.id == activity.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    act_date = activity.date
    if not isinstance(act_date, datetime.date):
        raise HTTPException(status_code=400, detail="Activity date invalid")

    # Only one claim per user per day
    existing_claim = db.query(Claim).filter(Claim.user_id == user.id, Claim.date == act_date).first()
    if existing_claim:
        return {"message": "User already has a claim for this date", "claim": {"km": existing_claim.km}}

    # Determine month to use (allow simulating November for tests)
    month_to_check = 11 if simulate_november else act_date.month

    # Only process November activities unless simulate_november is True
    if month_to_check != 11:
        return {"message": "Activity is outside November; ignored for challenge."}

    day = act_date.day
    max_allowed = 30 if day == 30 else 29

    # floor distance
    if activity.distance_km is None:
        raise HTTPException(status_code=400, detail="Activity distance missing")
    floor_km = int(activity.distance_km // 1)
    candidate_start = min(floor_km, max_allowed)

    # search from candidate_start down to 1 for an available km not yet claimed by anyone
    for k in range(candidate_start, 0, -1):
        taken = db.query(Claim).filter(Claim.km == k).first()
        if not taken:
            # create claim
            claim = Claim(user_id=user.id, km=k, date=act_date, activity_id=activity.id)
            db.add(claim)
            # mark activity and update user score
            activity.status = "claimed"
            user.total_score = (user.total_score or 0) + k
            db.commit()
            db.refresh(claim)
            return {"message": "Claim created", "km": k}
    return {"message": "No available km to claim for this activity"}


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

    # process newly created activity
    return process_activity(activity.id, simulate_november, db)