from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from models.activity import Activity
from models.claim import Claim
from models.user import User
from database import get_db
import datetime
import requests
import os
import traceback
from typing import Optional, List, Tuple, Dict, Any
import logging

router = APIRouter()

# -------------------------------------------------
# Konfiguration
# -------------------------------------------------
CHALLENGE_YEAR = 2025
CHALLENGE_MONTH = 11  # November

STRAVA_API_BASE = "https://www.strava.com/api/v3"
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
DEBUG_ERRORS = os.getenv("DEBUG_ERRORS", "0") in ("1", "true", "True")

# -------------------------------------------------
# Utils
# -------------------------------------------------
def _json_error(status: int, msg: str, extra: Dict[str, Any] = None, exc: Exception = None):
    payload = {"status": "error", "message": msg}
    if extra:
        payload.update(extra)
    if DEBUG_ERRORS and exc is not None:
        payload["exception"] = str(exc)
        payload["traceback"] = traceback.format_exc()
    return JSONResponse(status_code=status, content=payload)

def _month_bounds(year: int, month: int) -> Tuple[datetime.date, datetime.date]:
    first = datetime.date(year, month, 1)
    if month == 12:
        nxt = datetime.date(year + 1, 1, 1)
    else:
        nxt = datetime.date(year, month + 1, 1)
    last = nxt - datetime.timedelta(days=1)
    return first, last

def _in_challenge_window(d: datetime.date, month: int = None) -> bool:
    """Check if date is in challenge window (Nov of current/prev year)."""
    if month is None:
        month = CHALLENGE_MONTH
    # Allow current year or previous year (in case event started late)
    today = datetime.date.today()
    year = today.year
    # If we're before the challenge month, it might be from last year's running event
    if today.month < month:
        year -= 1
    return d.year == year and d.month == month

def _parse_activity_date_from_payload(data: Dict[str, Any]) -> datetime.date:
    """
    Parse activity date from Strava payload.
    PRIORITY: Always use start_date_local (athlete's local time).
    Only use start_date as fallback if start_date_local missing.
    NEVER convert UTC — always interpret as local time.
    """
    # PREFER start_date_local (it's already athlete's local time, no conversion needed)
    start = data.get("start_date_local")
    
    # Only fallback to start_date if start_date_local is missing
    if not start:
        start = data.get("start_date")
    
    if not start:
        raise ValueError("activity missing both start_date_local and start_date")
    
    s = str(start).strip()
    logging.debug(f"_parse_activity_date_from_payload: raw input = {s}, is_start_date_local={bool(data.get('start_date_local'))}")
    
    try:
        # Step 1: Remove timezone info completely (treat all as local time)
        # Format examples:
        # - "2025-11-01T00:40:00.000Z" (Z suffix — remove it, treat as local)
        # - "2025-11-01T00:40:00.000+00:00" (offset — remove it, treat as local)
        # - "2025-11-01T00:40:00.000-05:00" (offset — remove it, treat as local)
        # - "2025-11-01T00:40:00" (no tz — already local)
        
        # Remove 'Z' suffix if present
        if s.endswith('Z'):
            s = s[:-1]
        
        # Remove timezone offset (+/-HH:MM) if present
        if '+' in s:
            s = s.split('+')[0]
        
        # For negative offset, be careful (date has dashes too)
        # Only remove if after time part (after 'T')
        if 'T' in s and '-' in s:
            date_part, time_part = s.split('T', 1)
            # time_part might have negative offset like "00:40:00-05:00"
            if '-' in time_part:
                time_clean = time_part.split('-')[0]
                s = f"{date_part}T{time_clean}"
        
        # Remove milliseconds if present (not needed for date)
        if '.' in s:
            s = s.split('.')[0]
        
        logging.debug(f"_parse_activity_date_from_payload: cleaned = {s}")
        
        # Step 2: Parse as ISO format (NO timezone conversion — treat as local)
        dt = datetime.datetime.fromisoformat(s)
        result_date = dt.date()
        
        logging.debug(f"_parse_activity_date_from_payload: final result = {result_date} (year={result_date.year}, month={result_date.month}, day={result_date.day})")
        return result_date
        
    except Exception as e:
        logging.error(f"_parse_activity_date_from_payload failed on: {s}, error: {e}")
        raise ValueError(f"cannot parse start_date: {start}") from e

def _normalize_type(raw: Optional[str]) -> str:
    return (raw or "").lower().strip().replace(" ", "")

def _is_allowed_run_type(raw: Optional[str]) -> bool:
    return _normalize_type(raw) in {"run", "trailrun", "virtualrun"}

def _current_month_claims(db: Session, user_id: int) -> List[Claim]:
    first, last = _month_bounds(CHALLENGE_YEAR, CHALLENGE_MONTH)
    return db.query(Claim).filter(
        Claim.user_id == user_id,
        Claim.date >= first,
        Claim.date <= last
    ).all()

def _rebuild_user_slots_and_score_from_claims(user: User, claims: List[Claim]) -> None:
    # FIX: Erstelle Liste von integers, nicht dict
    taken = {int(c.km) for c in claims if getattr(c, "km", None) is not None}
    taken = {k for k in taken if 1 <= k <= 30}
    # Spiegel für Frontend: Liste mit km oder None
    user.slots = [k if (k in taken) else None for k in range(1, 31)]
    # Score = Summe belegter Slots
    user.total_score = sum(taken)
    try:
        flag_modified(user, "slots")
    except Exception:
        pass

def _can_refresh(user: User) -> bool:
    return bool(STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET and getattr(user, "refresh_token", None))

def _refresh_token(user: User) -> Optional[str]:
    if not _can_refresh(user):
        return None
    try:
        resp = requests.post(
            f"{STRAVA_API_BASE}/oauth/token",
            data={
                "client_id": STRAVA_CLIENT_ID,
                "client_secret": STRAVA_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": user.refresh_token,
            },
            timeout=12,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        new_access = data.get("access_token")
        if new_access:
            user.access_token = new_access
        if data.get("refresh_token"):
            try:
                user.refresh_token = data["refresh_token"]
            except Exception:
                pass
        if data.get("expires_at"):
            try:
                user.token_expires_at = int(data["expires_at"])
            except Exception:
                pass
        return new_access
    except Exception:
        return None

def _strava_get(path: str, token: str, params: Dict[str, Any] = None) -> requests.Response:
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(f"{STRAVA_API_BASE}{path}", headers=headers, params=params or {}, timeout=15)

# -------------------------------------------------
# Core Processing
# -------------------------------------------------
def process_activity_instance(activity: Activity, db: Session, simulate_month: int = None) -> Dict[str, Any]:
    """
    Process a single activity instance.
    simulate_month: optional override for testing (defaults to CHALLENGE_MONTH env).
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

    # Use simulate_month for testing, otherwise use CHALLENGE_MONTH
    month_to_check = simulate_month if simulate_month is not None else CHALLENGE_MONTH
    
    if not _in_challenge_window(act_date, month_to_check):
        return {"message": f"Activity is outside challenge window; ignored."}

    # nur 1 Claim/Tag
    existing_claim = db.query(Claim).filter(
        Claim.user_id == user.id,
        Claim.date == act_date
    ).first()
    if existing_claim:
        return {"message": "User already has a claim for this date", "claim": {"km": existing_claim.km}}

    if activity.distance_km is None:
        return {"error": "Activity distance missing"}

    # Zielslot: floor(distance_km), begrenzt 1..30 (keine obere Grenze mehr — nur minimum 1)
    floor_km = int(float(activity.distance_km) // 1)
    # REMOVED 30-km limit: allow any km value >= 1
    candidate_start = max(floor_km, 1)

    monthly_claims = _current_month_claims(db, user.id)
    taken = {int(c.km) for c in monthly_claims if getattr(c, "km", None) is not None and 1 <= int(c.km)}

    assigned = None
    # NEW: search from candidate down to 1, but also allow going ABOVE 30 if candidate > 30
    for k in range(candidate_start, 0, -1):
        if k not in taken:
            assigned = k
            break

    if not assigned:
        return {"message": "No available km to claim for this activity"}

    # Claim anlegen + Activity markieren
    claim = Claim(user_id=user.id, km=assigned, date=act_date, activity_id=activity.id)
    db.add(claim)

    activity.status = "claimed"
    activity.effective_km = assigned
    db.add(activity)

    # Slots/Score neu spiegeln
    db.flush()
    monthly_claims = _current_month_claims(db, user.id)
    _rebuild_user_slots_and_score_from_claims(user, monthly_claims)
    db.add(user)

    db.commit()
    db.refresh(claim)
    return {"message": "Claim created", "km": assigned}

# -------------------------------------------------
# Routes
# -------------------------------------------------
@router.get("/health")
def health():
    return {"status": "ok", "challenge": f"{CHALLENGE_YEAR}-{CHALLENGE_MONTH:02d}"}

@router.get("/")
def get_all_activities(db: Session = Depends(get_db)):
    try:
        return db.query(Activity).all()
    except Exception as e:
        return _json_error(500, "DB query failed", exc=e)

@router.post("/process/{activity_id}")
def process_activity(activity_id: int, db: Session = Depends(get_db)):
    try:
        activity = db.query(Activity).filter(Activity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        result = process_activity_instance(activity, db)
        if "error" in result:
            return _json_error(400, result["error"])
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        return _json_error(500, "Processing failed", {"activity_id": activity_id}, e)

@router.post("/process_by_strava/{strava_activity_id}")
def process_by_strava(
    strava_activity_id: int,
    owner_strava_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    try:
        # Schon vorhanden?
        existing = db.query(Activity).filter(Activity.strava_id == str(strava_activity_id)).first()
        if existing:
            result = process_activity_instance(existing, db)
            if "error" in result:
                return _json_error(400, result["error"])
            return result

        # Nutzer bestimmen
        if owner_strava_id is not None:
            user = db.query(User).filter(User.strava_id == owner_strava_id).first()
        else:
            user = db.query(User).first()
        if not user:
            return _json_error(404, "User not found (provide owner_strava_id if multiple users exist)")

        token = getattr(user, "access_token", None)
        if not token:
            return _json_error(400, "User has no access_token", {"owner_strava_id": getattr(user, "strava_id", None)})

        # 1. Versuch
        r = _strava_get(f"/activities/{strava_activity_id}", token)

        # 401 -> Refresh (falls möglich) und Retry
        if r.status_code == 401 and _can_refresh(user):
            new_token = _refresh_token(user)
            if new_token:
                db.add(user)
                db.commit()
                r = _strava_get(f"/activities/{strava_activity_id}", new_token)

        if r.status_code != 200:
            return _json_error(502, "Strava fetch failed",
                               {"code": r.status_code, "body": r.text, "path": f"/activities/{strava_activity_id}"})

        data = r.json()
        if not _is_allowed_run_type(data.get("type")):
            return {"status": "ignored_non_run", "type": data.get("type"), "allowed": ["Run", "TrailRun", "VirtualRun"]}

        distance_m = data.get("distance", 0) or 0
        distance_km = float(distance_m) / 1000.0

        act_date = _parse_activity_date_from_payload(data)
        if not _in_challenge_window(act_date):
            return {"message": "Activity is outside challenge window (Nov 2025); ignored."}

        # Activity anlegen
        activity = Activity(
            user_id=user.id,
            strava_id=str(strava_activity_id),
            date=act_date,
            distance_km=distance_km,
            status="fetched"
        )
        db.add(activity)
        db.commit()
        db.refresh(activity)

        # Verarbeiten
        result = process_activity_instance(activity, db)
        if "error" in result:
            return _json_error(400, result["error"])
        return result

    except HTTPException as he:
        raise he
    except Exception as e:
        return _json_error(500, "process_by_strava failed",
                           {"strava_activity_id": str(strava_activity_id), "owner_strava_id": owner_strava_id}, e)

@router.post("/sync_recent/{owner_strava_id}")
def sync_recent(owner_strava_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.strava_id == owner_strava_id).first()
        if not user:
            return _json_error(404, "User not found", {"owner_strava_id": owner_strava_id})

        token = getattr(user, "access_token", None)
        if not token:
            return _json_error(400, "User has no access_token", {"owner_strava_id": owner_strava_id})

        first_day, last_day = _month_bounds(CHALLENGE_YEAR, CHALLENGE_MONTH)
        after_epoch = int(datetime.datetime(first_day.year, first_day.month, first_day.day, 0, 0, 0,
                                            tzinfo=datetime.timezone.utc).timestamp())
        before_epoch = int(datetime.datetime(last_day.year, last_day.month, last_day.day, 23, 59, 59,
                                             tzinfo=datetime.timezone.utc).timestamp())

        params = {"per_page": 50, "page": 1, "after": after_epoch, "before": before_epoch}
        r = _strava_get("/athlete/activities", token, params=params)

        if r.status_code == 401 and _can_refresh(user):
            new_token = _refresh_token(user)
            if new_token:
                db.add(user)
                db.commit()
                r = _strava_get("/athlete/activities", new_token, params=params)

        if r.status_code != 200:
            return _json_error(502, "Strava activities fetch failed",
                               {"code": r.status_code, "body": r.text, "path": "/athlete/activities"})

        items = r.json() or []
        created, processed, skipped = 0, 0, 0

        for it in items:
            if not _is_allowed_run_type(it.get("type")):
                skipped += 1
                continue
            try:
                act_date = _parse_activity_date_from_payload(it)
            except Exception:
                skipped += 1
                continue
            if not _in_challenge_window(act_date):
                skipped += 1
                continue

            sid = str(it.get("id") or "")
            if not sid.isdigit():
                skipped += 1
                continue

            dist_km = float((it.get("distance", 0) or 0)) / 1000.0

            existing = db.query(Activity).filter(Activity.strava_id == sid).first()
            if existing:
                if not existing.distance_km:
                    existing.distance_km = dist_km
                if not existing.date:
                    existing.date = act_date
                db.add(existing)
                res = process_activity_instance(existing, db)
                if res.get("message") == "Claim created":
                    processed += 1
                else:
                    skipped += 1
                continue

            try:
                activity = Activity(
                    user_id=user.id,
                    strava_id=sid,
                    date=act_date,
                    distance_km=dist_km,
                    status="fetched"
                )
                db.add(activity)
                db.commit()
                db.refresh(activity)
                created += 1
            except Exception:
                db.rollback()
                skipped += 1
                continue

        return {            "skipped": skipped            "processed_claims": processed,            "created_in_db": created,            "fetched": len(items),            "owner_strava_id": owner_strava_id,            "status": "ok",        }
    except Exception as e:
        return _json_error(500, "sync_recent failed", {"owner_strava_id": owner_strava_id}, e)    except Exception as e:        raise he    except HTTPException as he:        }            "skipped": skipped            "processed_claims": processed,            "created_in_db": created,            "fetched": len(items),            "owner_strava_id": owner_strava_id,            "status": "ok",        return {                skipped += 1            else:                processed += 1            if res.get("message") == "Claim created":            res = process_activity_instance(activity, db)# NEW: Debug endpoint to inspect stored activities
@router.get("/debug/activities")
def debug_activities(user_id: int = None, db: Session = Depends(get_db)):
    """
    Debug endpoint: show all activities with raw dates for inspection.
    Pass ?user_id=123 to filter by user.
    """
    try:
        query = db.query(Activity)
        if user_id:
            query = query.filter(Activity.user_id == user_id)
        activities = query.all()
        
        result = []
        for act in activities:
            result.append({
                "id": act.id,
                "user_id": act.user_id,
                "strava_id": act.strava_id,
                "date_raw": str(act.date) if act.date else None,  # Show raw date
                "date_day": act.date.day if act.date else None,
                "date_month": act.date.month if act.date else None,
                "date_year": act.date.year if act.date else None,
                "distance_km": float(act.distance_km or 0),
                "effective_km": act.effective_km,
                "status": act.status,
                "is_manual": act.is_manual,
                "strava_id": act.strava_id
            })
        
        return {
            "count": len(result),
            "activities": sorted(result, key=lambda x: x["date_raw"] or "", reverse=True)
        }
    except Exception as e:
        return {"error": str(e)}
