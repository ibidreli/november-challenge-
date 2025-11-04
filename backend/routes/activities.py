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

logger = logging.getLogger(__name__)
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
    Prioritize start_date_local (which is already in the athlete's local time).
    Ignore UTC offset in both fields.
    """
    start = data.get("start_date_local") or data.get("start_date")
    if not start:
        raise ValueError("activity missing start_date")
    
    s = str(start).strip()
    
    # Remove timezone info (Z, +00:00, etc.) — we want local time as-is
    # Split on 'T' and take date part, or parse datetime and extract date
    try:
        # Remove any timezone suffix
        if "+" in s:
            s = s.split("+")[0]
        if "-" in s and "T" in s:
            # Be careful: YYYY-MM-DD has dashes, but so does timezone offset
            # Only remove if it's after the time part
            parts = s.split("T")
            if len(parts) == 2:
                time_part = parts[1]
                if "-" in time_part:  # timezone offset like 2000-01-23T04:56:07.000-05:00
                    s = parts[0] + "T" + time_part.split("-")[0]
        if s.endswith("Z"):
            s = s[:-1]
        
        # Parse as local datetime (no timezone conversion)
        # Try full ISO format first
        try:
            dt = datetime.datetime.fromisoformat(s)
        except ValueError:
            # Fallback: just take date part
            date_part = s.split("T")[0]
            dt = datetime.datetime.fromisoformat(date_part)
        
        return dt.date()
    except Exception as e:
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
    """
    ÜBERARBEITETE LOGIK:
    - Respektiere bestehende manuelle Einträge in user.slots
    - Berechne Score als Summe aller belegten Slots (whether from claims or manual)
    - Nur Claims hinzufügen, wo noch kein Slot gesetzt ist
    """
    user.ensure_slots()
    
    # Schritt 1: Bestehende Slots kopieren (respektiere manuelle Änderungen!)
    current_slots = list(user.slots or [None] * 30)
    
    # Schritt 2: Welche km sind bereits belegt? (von Hand ODER durch Claims)
    taken_km = set()
    for i, slot_value in enumerate(current_slots):
        if slot_value is not None:
            km_value = int(slot_value)
            if 1 <= km_value <= 30:
                taken_km.add(km_value)
    
    # Schritt 3: Claims hinzufügen, nur wo noch nicht belegt
    for claim in claims:
        claim_km = int(getattr(claim, "km", 0) or 0)
        if 1 <= claim_km <= 30 and claim_km not in taken_km:
            current_slots[claim_km - 1] = claim_km  # Index = km - 1
            taken_km.add(claim_km)
    
    # Schritt 4: Score = Summe aller belegten Slots (nicht nur Claims!)
    user.slots = current_slots
    user.total_score = sum(taken_km)
    
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
    
    WICHTIG: Neue Logik respektiert bestehende Slots!
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

    # Zielslot: floor(distance_km), begrenzt auf minimum 1
    floor_km = int(float(activity.distance_km) // 1)
    candidate_start = max(floor_km, 1)

    # WICHTIG: Achte auf BESTEHENDE SLOTS (auch manuelle Änderungen!)
    user.ensure_slots()
    current_slots = list(user.slots or [None] * 30)
    
    # Welche km sind BEREITS BELEGT (egal ob durch Claim oder manuell)?
    taken = set()
    for i, slot_value in enumerate(current_slots):
        if slot_value is not None:
            km_val = int(slot_value)
            if 1 <= km_val <= 30:
                taken.add(km_val)

    assigned = None
    # Suche freien Slot von candidate_start abwärts
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

    # Slots/Score neu spiegeln (respektiert manuelle Änderungen!)
    db.flush()
    monthly_claims = _current_month_claims(db, user.id)
    _rebuild_user_slots_and_score_from_claims(user, monthly_claims)
    db.add(user)

    db.commit()
    db.refresh(claim)
    logger.info(f"Activity {activity.id} processed: claimed km={assigned} for user {user.id}")
    return {"message": "Claim created", "km": assigned}

# -------------------------------------------------
# NEUE FUNKTION: Interner Sync (für Background-Task)
# -------------------------------------------------
def sync_recent_internal(owner_strava_id: int, db: Session) -> Dict[str, Any]:
    """
    Interne Sync-Logik (wird von Background-Task + Manual-Endpoint verwendet).
    EXTRA LOGGING für Debugging von fehlenden Aktivitäten.
    """
    try:
        user = db.query(User).filter(User.strava_id == owner_strava_id).first()
        if not user:
            logger.warning(f"sync_recent_internal: User not found for strava_id {owner_strava_id}")
            return {"error": "User not found", "owner_strava_id": owner_strava_id}

        token = getattr(user, "access_token", None)
        if not token:
            logger.warning(f"sync_recent_internal: No token for user {user.id} (strava_id {owner_strava_id})")
            return {"error": "User has no access_token", "owner_strava_id": owner_strava_id}

        first_day, last_day = _month_bounds(CHALLENGE_YEAR, CHALLENGE_MONTH)
        after_epoch = int(datetime.datetime(first_day.year, first_day.month, first_day.day, 0, 0, 0,
                                            tzinfo=datetime.timezone.utc).timestamp())
        before_epoch = int(datetime.datetime(last_day.year, last_day.month, last_day.day, 23, 59, 59,
                                             tzinfo=datetime.timezone.utc).timestamp())

        params = {"per_page": 50, "page": 1, "after": after_epoch, "before": before_epoch}
        
        logger.debug(f"Fetching Strava activities for user {user.id}: after={after_epoch}, before={before_epoch}")
        r = _strava_get("/athlete/activities", token, params=params)

        if r.status_code == 401 and _can_refresh(user):
            logger.info(f"Token expired for user {user.id}, refreshing...")
            new_token = _refresh_token(user)
            if new_token:
                db.add(user)
                db.commit()
                r = _strava_get("/athlete/activities", new_token, params=params)

        if r.status_code != 200:
            logger.error(f"Strava fetch failed for user {user.id}: {r.status_code} {r.text}")
            return {"error": "Strava fetch failed", "code": r.status_code}

        items = r.json() or []
        logger.info(f"Strava returned {len(items)} activities for user {user.id}")
        
        created, processed, skipped = 0, 0, 0
        skipped_reasons = []

        for idx, it in enumerate(items):
            try:
                act_type = it.get("type")
                if not _is_allowed_run_type(act_type):
                    logger.debug(f"  [{idx}] Activity {it.get('id')}: Skipped - type '{act_type}' not allowed")
                    skipped += 1
                    skipped_reasons.append(f"type={act_type}")
                    continue
                
                try:
                    act_date = _parse_activity_date_from_payload(it)
                except Exception as e:
                    logger.debug(f"  [{idx}] Activity {it.get('id')}: Skipped - date parse error: {e}")
                    skipped += 1
                    skipped_reasons.append(f"date_parse_error")
                    continue
                
                if not _in_challenge_window(act_date):
                    logger.debug(f"  [{idx}] Activity {it.get('id')} ({act_date}): Skipped - outside challenge window")
                    skipped += 1
                    skipped_reasons.append(f"outside_window")
                    continue

                sid = str(it.get("id") or "")
                if not sid.isdigit():
                    logger.debug(f"  [{idx}] Activity: Skipped - invalid id '{sid}'")
                    skipped += 1
                    skipped_reasons.append(f"invalid_id")
                    continue

                dist_km = float((it.get("distance", 0) or 0)) / 1000.0
                activity_name = it.get("name", "N/A")

                existing = db.query(Activity).filter(Activity.strava_id == sid).first()
                if existing:
                    if not existing.distance_km:
                        existing.distance_km = dist_km
                    if not existing.date:
                        existing.date = act_date
                    db.add(existing)
                    res = process_activity_instance(existing, db)
                    if res.get("message") == "Claim created":
                        logger.info(f"  [{idx}] Activity {sid} (existing): CLAIMED km={res.get('km')}")
                        processed += 1
                    else:
                        logger.debug(f"  [{idx}] Activity {sid} (existing): {res}")
                        skipped += 1
                        skipped_reasons.append(f"process_result={res.get('message', 'unknown')}")
                    continue

                logger.info(f"  [{idx}] Activity {sid} '{activity_name}' ({act_date}, {dist_km}km): Creating...")
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
                logger.info(f"  [{idx}] Activity {sid}: Created in DB")

                res = process_activity_instance(activity, db)
                if res.get("message") == "Claim created":
                    logger.info(f"  [{idx}] Activity {sid}: CLAIMED km={res.get('km')}")
                    processed += 1
                else:
                    logger.debug(f"  [{idx}] Activity {sid}: {res}")
                    skipped += 1
                    skipped_reasons.append(f"process_result={res.get('message', 'unknown')}")

            except Exception as e:
                logger.error(f"  [{idx}] Exception processing activity: {e}", exc_info=True)
                db.rollback()
                skipped += 1
                skipped_reasons.append(f"exception")

        logger.info(f"Sync complete for user {user.id}: created={created}, processed={processed}, skipped={skipped}")
        if skipped_reasons:
            logger.debug(f"Skipped reasons: {skipped_reasons}")
        
        return {
            "status": "ok",
            "owner_strava_id": owner_strava_id,
            "fetched": len(items),
            "created_in_db": created,
            "processed_claims": processed,
            "skipped": skipped
        }

    except Exception as e:
        logger.error(f"sync_recent_internal failed for strava_id {owner_strava_id}: {e}", exc_info=True)
        return {"error": "sync_recent_internal failed", "owner_strava_id": owner_strava_id, "exception": str(e)}

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
    """
    MANUELLER Sync-Endpoint (für On-Demand Refresh).
    Frontend kann damit einen manuellen Refresh triggern.
    """
    try:
        from tasks.sync_scheduler import mark_sync_done
        result = sync_recent_internal(owner_strava_id, db)
        if "error" not in result:
            # Markiere als gerade synced (für Auto-Sync Timing)
            user = db.query(User).filter(User.strava_id == owner_strava_id).first()
            if user:
                mark_sync_done(user.id)
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"sync_recent endpoint failed: {e}", exc_info=True)
        return _json_error(500, "sync_recent failed", {"owner_strava_id": owner_strava_id}, e)

# NEU: Endpoint für Debug-Infos (wie lange bis nächster Auto-Sync)
@router.get("/sync_status/{owner_strava_id}")
def get_sync_status(owner_strava_id: int, db: Session = Depends(get_db)):
    """
    Zeige Sync-Status für einen User:
    - Wann war der letzte Sync?
    - Wann ist der nächste Auto-Sync geplant?
    """
    try:
        from tasks.sync_scheduler import get_seconds_until_next_sync
        user = db.query(User).filter(User.strava_id == owner_strava_id).first()
        if not user:
            return {"error": "User not found"}
        
        seconds_until = get_seconds_until_next_sync(user.id)
        return {
            "user_id": user.id,
            "strava_id": owner_strava_id,
            "seconds_until_next_auto_sync": seconds_until,
            "minutes_until_next_auto_sync": round(seconds_until / 60, 1),
            "auto_sync_interval_seconds": 900
        }
    except Exception as e:
        logger.error(f"get_sync_status failed: {e}")
        return _json_error(500, "Failed to get sync status", exc=e)
