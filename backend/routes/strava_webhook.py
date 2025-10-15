from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models.user import User
from models.activity import Activity
from models.claim import Claim
import os, requests
import datetime
from sqlalchemy.orm.attributes import flag_modified
import time
import logging

router = APIRouter()

STRAVA_API_BASE = "https://www.strava.com/api/v3/activities/"

@router.get("/webhook")
async def verify_challenge(request: Request):
    params = dict(request.query_params)
    if "hub.challenge" in params:
        return PlainTextResponse(params["hub.challenge"])
    return JSONResponse({"status": "ok"})

@router.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    payload = await request.json()
    obj_type = payload.get("object_type")
    aspect = payload.get("aspect_type")
    owner_id = payload.get("owner_id")
    object_id = payload.get("object_id")

    if obj_type != "activity" or object_id is None or owner_id is None:
        return JSONResponse({"status": "ignored"})

    user = db.query(User).filter_by(strava_id=owner_id).first()
    if not user:
        return JSONResponse({"status": "user_not_found", "owner_id": owner_id})

    access_token = user.access_token
    if not access_token:
        return JSONResponse({"status": "no_token", "user_id": user.id})

    # Try immediate fetch once
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        r = requests.get(STRAVA_API_BASE + str(object_id), headers=headers, timeout=10)
        if r.status_code != 200:
            # schedule background retry and return accepted
            background_tasks.add_task(fetch_and_process_activity, owner_id, object_id)
            return JSONResponse({"status": "scheduled_retry"})
        data = r.json()
        distance_m = data.get("distance", 0)
        distance_km = (distance_m or 0) / 1000.0
        start = data.get("start_date_local") or data.get("start_date")
        if start and start.endswith("Z"):
            start = start[:-1]
        if start:
            dt = datetime.datetime.fromisoformat(start)
            act_date = dt.date()
        else:
            act_date = datetime.date.today()
    except Exception as e:
        # schedule background retry on exception
        background_tasks.add_task(fetch_and_process_activity, owner_id, object_id)
        return JSONResponse({"status": "scheduled_retry", "error": str(e)}, status_code=202)

    # ensure Activity exists in DB (create if missing)
    activity = db.query(Activity).filter(Activity.strava_id == str(object_id)).first()
    try:
        if not activity:
            activity = Activity(user_id=user.id, strava_id=str(object_id), date=act_date, distance_km=distance_km, status="fetched")
            db.add(activity)
            db.commit()
            db.refresh(activity)
    except Exception as e:
        db.rollback()
        return JSONResponse({"status": "db_error_creating_activity", "error": str(e)}, status_code=500)

    # compute daily cap and candidate_start
    day = activity.date.day if activity.date else datetime.date.today().day
    max_allowed = 30 if day == 30 else 29
    candidate_start = min(int((activity.distance_km or 0) // 1), max_allowed)

    # assign slot via user's helper (this updates slots and total_score)
    assigned_km = user.assign_activity(candidate_start, activity.id)
    if assigned_km:
        try:
            claim = Claim(user_id=user.id, km=assigned_km, date=activity.date or datetime.date.today(), activity_id=activity.id)
            db.add(claim)
            activity.effective_km = assigned_km
            activity.status = "claimed"
            try:
                flag_modified(user, "slots")
            except Exception:
                pass
            db.add(user)
            db.add(activity)
            db.commit()
            db.refresh(claim)
            return JSONResponse({"status": "ok", "assigned_km": assigned_km, "total_score": user.total_score})
        except Exception as e:
            db.rollback()
            return JSONResponse({"status": "db_error_claim", "error": str(e)}, status_code=500)
    else:
        try:
            user.ensure_slots()
            flag_modified(user, "slots")
            db.add(user)
            db.commit()
        except Exception:
            db.rollback()
        return JSONResponse({"status": "no_slot_available", "total_score": user.total_score})


# Background retry helper (runs in background thread)
def fetch_and_process_activity(owner_id: int, object_id: int, attempts: int = 6, initial_delay: int = 5):
    db = SessionLocal()
    try:
        for attempt in range(attempts):
            try:
                user = db.query(User).filter_by(strava_id=owner_id).first()
                if not user or not user.access_token:
                    logging.warning("Background fetch: user missing or no token for owner %s", owner_id)
                    return
                headers = {"Authorization": f"Bearer {user.access_token}"}
                r = requests.get(STRAVA_API_BASE + str(object_id), headers=headers, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    distance_m = data.get("distance", 0)
                    distance_km = (distance_m or 0) / 1000.0
                    start = data.get("start_date_local") or data.get("start_date")
                    if start and start.endswith("Z"):
                        start = start[:-1]
                    if start:
                        dt = datetime.datetime.fromisoformat(start)
                        act_date = dt.date()
                    else:
                        act_date = datetime.date.today()
                    # ensure Activity exists
                    activity = db.query(Activity).filter(Activity.strava_id == str(object_id)).first()
                    try:
                        if not activity:
                            activity = Activity(user_id=user.id, strava_id=str(object_id), date=act_date, distance_km=distance_km, status="fetched")
                            db.add(activity)
                            db.commit()
                            db.refresh(activity)
                    except Exception:
                        db.rollback()
                        logging.exception("Background fetch: failed to create activity")
                        return
                    # compute cap and assign
                    day = activity.date.day if activity.date else datetime.date.today().day
                    max_allowed = 30 if day == 30 else 29
                    candidate_start = min(int((activity.distance_km or 0) // 1), max_allowed)
                    assigned_km = user.assign_activity(candidate_start, activity.id)
                    if assigned_km:
                        try:
                            claim = Claim(user_id=user.id, km=assigned_km, date=activity.date or datetime.date.today(), activity_id=activity.id)
                            db.add(claim)
                            activity.effective_km = assigned_km
                            activity.status = "claimed"
                            try:
                                flag_modified(user, "slots")
                            except Exception:
                                pass
                            db.add(user)
                            db.add(activity)
                            db.commit()
                            logging.info("Background fetch: processed activity %s for owner %s (km=%s)", object_id, owner_id, assigned_km)
                        except Exception:
                            db.rollback()
                            logging.exception("Background fetch: failed to persist claim")
                    else:
                        # persist ensure_slots so frontend shows correct slots array
                        try:
                            user.ensure_slots()
                            flag_modified(user, "slots")
                            db.add(user)
                            db.commit()
                        except Exception:
                            db.rollback()
                    return
                else:
                    # not ready yet, wait and retry
                    wait = initial_delay * (2 ** attempt)
                    time.sleep(wait)
            except Exception:
                # transient error, wait and retry
                wait = initial_delay * (2 ** attempt)
                time.sleep(wait)
        logging.warning("Background fetch: giving up after %s attempts for activity %s owner %s", attempts, object_id, owner_id)
    finally:
        db.close()
