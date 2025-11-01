from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
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
    """
    Handle Strava webhook events.
    """
    try:
        payload = await request.json()
    except Exception as e:
        logging.warning("Failed to parse webhook payload: %s", e)
        return JSONResponse({"status": "parse_error"})
    
    obj_type = payload.get("object_type")
    aspect = payload.get("aspect_type")
    owner_id = payload.get("owner_id")
    object_id = payload.get("object_id")

    if obj_type != "activity" or object_id is None or owner_id is None:
        return JSONResponse({"status": "ignored"})

    user = db.query(User).filter_by(strava_id=owner_id).first()
    if not user:
        # NEW: Silently ignore unknown users instead of failing
        logging.debug("Webhook: unknown strava_id=%s", owner_id)
        return JSONResponse({"status": "user_not_found"})

    access_token = user.access_token
    if not access_token:
        # NEW: Schedule background retry instead of failing immediately
        logging.info("Webhook: no token for user %s, scheduling background fetch", user.id)
        background_tasks.add_task(fetch_and_process_activity, owner_id, object_id, user.id)
        return JSONResponse({"status": "scheduled_background"})

    # Try immediate fetch, but don't fail if it doesn't work
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        r = requests.get(STRAVA_API_BASE + str(object_id), headers=headers, timeout=10)
        if r.status_code != 200:
            # Schedule background retry
            logging.info("Webhook: immediate fetch failed (status %s), scheduling retry", r.status_code)
            background_tasks.add_task(fetch_and_process_activity, owner_id, object_id, user.id)
            return JSONResponse({"status": "scheduled_retry"})
        data = r.json()
    except Exception as e:
        logging.warning("Webhook: immediate fetch exception, scheduling retry: %s", e)
        background_tasks.add_task(fetch_and_process_activity, owner_id, object_id, user.id)
        return JSONResponse({"status": "scheduled_retry"})

    # Process fetched activity
    return _process_webhook_activity(user, object_id, data, db)


def _process_webhook_activity(user: User, object_id: int, data: dict, db: Session):
    """
    Shared logic to process webhook activity data.
    FIX: db.close() Fehler behandelt
    """
    try:
        # ignore non-Run activities
        if (data.get("type") or "").lower() not in {"run", "trail run", "virtual run"}:
            return JSONResponse({"status": "ignored_non_run", "type": data.get("type")})
        
        distance_m = data.get("distance", 0)
        distance_km = (distance_m or 0) / 1000.0
        
        # Parse date robustly (use start_date_local if available)
        start = data.get("start_date_local") or data.get("start_date")
        if not start:
            return JSONResponse({"status": "no_start_date"})
        
        # Strip timezone info and parse as local time
        s = str(start).strip()
        if "+" in s:
            s = s.split("+")[0]
        if "-" in s and "T" in s:
            parts = s.split("T")
            if len(parts) == 2 and "-" in parts[1]:
                s = parts[0] + "T" + parts[1].split("-")[0]
        if s.endswith("Z"):
            s = s[:-1]
        
        try:
            dt = datetime.datetime.fromisoformat(s)
        except ValueError:
            date_part = s.split("T")[0]
            dt = datetime.datetime.fromisoformat(date_part)
        
        act_date = dt.date()
    except Exception as e:
        logging.warning("Webhook: failed to parse activity date: %s", e)
        return JSONResponse({"status": "date_parse_error"})

    # ensure Activity exists in DB
    activity = db.query(Activity).filter(Activity.strava_id == str(object_id)).first()
    try:
        if not activity:
            activity = Activity(user_id=user.id, strava_id=str(object_id), date=act_date, distance_km=distance_km, status="fetched")
            db.add(activity)
            db.commit()
            db.refresh(activity)
    except Exception as e:
        db.rollback()
        logging.exception("Webhook: failed to create activity")
        return JSONResponse({"status": "db_error_creating_activity"}, status_code=500)

    # Process using shared logic
    try:
        from routes.activities import process_activity_instance
    except Exception:
        from backend.routes.activities import process_activity_instance
    
    try:
        result = process_activity_instance(activity, db)
        if "error" in result:
            return JSONResponse({"status": "processing_error", "error": result["error"]}, status_code=400)
        return JSONResponse({"status": "ok", "result": result})
    except Exception as e:
        logging.exception("Webhook: activity processing failed")
        return JSONResponse({"status": "processing_exception", "error": str(e)}, status_code=500)
    finally:
        # FIX: Stelle sicher db nicht doppelt geschlossen wird
        # (handle_webhook schließt nicht, nur background task)
        pass


# Background retry helper (runs in background thread)
def fetch_and_process_activity(owner_id: int, object_id: int, user_id: int = None, attempts: int = 6, initial_delay: int = 5):
    """
    Background task to fetch and process activity when immediate webhook processing isn't possible.
    Retries with exponential backoff.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(strava_id=owner_id).first()
        if not user or not user.access_token:
            logging.warning("Background fetch: user missing or no token for owner %s", owner_id)
            return

        for attempt in range(attempts):
            try:
                headers = {"Authorization": f"Bearer {user.access_token}"}
                r = requests.get(STRAVA_API_BASE + str(object_id), headers=headers, timeout=10)
                
                if r.status_code == 200:
                    data = r.json()
                    result = _process_webhook_activity(user, object_id, data, db)
                    logging.info("Background fetch succeeded for activity %s owner %s: %s", object_id, owner_id, result)
                    return
                else:
                    # 401 Unauthorized or other error — wait and retry
                    wait_time = initial_delay * (2 ** attempt)
                    logging.debug("Background fetch attempt %d failed (status %s), waiting %ds before retry", attempt + 1, r.status_code, wait_time)
                    time.sleep(wait_time)
            except Exception as e:
                wait_time = initial_delay * (2 ** attempt)
                logging.debug("Background fetch attempt %d exception: %s, waiting %ds", attempt + 1, e, wait_time)
                time.sleep(wait_time)
        
        logging.warning("Background fetch: giving up after %s attempts for activity %s owner %s", attempts, object_id, owner_id)
    except Exception as e:
        logging.exception("Background fetch fatal error: %s", e)
    finally:
        db.close()
