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
from typing import Optional, List, Tuple, Dict, Any

router = APIRouter()

# --- Challenge fest verdrahtet: nur November 2025 ---
CHALLENGE_YEAR = 2025
CHALLENGE_MONTH = 11  # November

STRAVA_API_BASE = "https://www.strava.com/api/v3"
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")


# -----------------------
# Hilfsfunktionen
# -----------------------

def _month_bounds(year: int, month: int) -> Tuple[datetime.date, datetime.date]:
    first = datetime.date(year, month, 1)
    if month == 12:
        nxt = datetime.date(year + 1, 1, 1)
    else:
        nxt = datetime.date(year, month + 1, 1)
    last = nxt - datetime.timedelta(days=1)
    return first, last


def _in_challenge_window(d: datetime.date) -> bool:
    return d.year == CHALLENGE_YEAR and d.month == CHALLENGE_MONTH


def _parse_activity_date_from_payload(data: Dict[str, Any]) -> datetime.date:
    """
    Holt Datum aus start_date_local (oder start_date). 'Z' -> '+00:00' (UTC). Gibt date() zurück.
    """
    start = data.get("start_date_local") or data.get("start_date")
    if not start:
        raise ValueError("activity missing start_date")
    s = start.replace("Z", "+00:00")
    dt = datetime.datetime.fromisoformat(s)
    return dt.date()


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
    Spiegel für Frontend + Score setzen (Score = Summe belegter km in Nov 2025).
    """
    taken = {int(c.km) for c in claims if c.km is not None and 1 <= int(c.km) <= 30}
    user.slots = {str(k): (k in taken) for k in range(1, 31)}
    user.total_score = sum(taken)
    try:
        flag_modified(user, "slots")
    except Exception:
        pass


def _ensure_valid_access_token(user: User) -> Optional[str]:
    """
    Gibt ein garantiert aktuelles Access Token zurück (falls refresh möglich),
    sonst das vorhandene. None, wenn keins verfügbar.
    """
    token = getattr(user, "access_token", None)
    # Wenn kein Token, können wir nichts tun
    if not token:
        return None

    # Optional: wenn expires_at vorhanden & abgelaufen -> refresh
    expires_at = getattr(user, "token_expires_at", None)
    need_refresh = False
    if expires_at:
        try:
            # expires_at könnte epoch sein
            now_epoch = int(datetime.datetime.utcnow().timestamp())
            if int(expires_at) <= now_epoch + 60:
                need_refresh = True
        except Exception:
            # Falls unlesbar, versuchen wir nur bei 401 zu refreshen
            pass

    if not need_refresh:
        return token

    return _refresh_token(user) or token


def _refresh_token(user: User) -> Optional[str]:
    refresh_token = getattr(user, "refresh_token", None)
    if not (STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET and refresh_token):
        return None

    try:
        resp = requests.post(
            f"{STRAVA_API_BASE}/oauth/token",
            data={
                "client_id": STRAVA_CLIENT_ID,
                "client_secret": STRAVA_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        new_access = data.get("access_token")
        new_refresh = data.get("refresh_token") or refresh_token
        new_expires_at = data.get("expires_at")

        # Update am User-Objekt (keine Schema-Änderung, Felder optional)
        if new_access:
            user.access_token = new_access
        if new_refresh:
            try:
                user.refresh_token = new_refresh
            except Exception:
                pass
        if new_expires_at:
            try:
                user.token_expires_at = int(new_expires_at)
            except Exception:
                pass
        return new_access
    except Exception:
        return None


def _strava_get(path: str, token: str, params: Dict[str, Any] = None) -> requests.Response:
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(f"{STRAVA_API_BASE}{path}", headers=headers, params=params or {}, timeout=12)


# -----------------------
# Kernlogik: Processing
# -----------------------

def process_activity_instance(activity: Activity, db: Session) -> Dict[str, Any]:
    """
    - Challenge NUR November 2025
    - 1 Claim pro Nutzer pro Tag
    - Keine 'Tag==30'-Sperre
    - Belegte km-Slots aus Monats-Claims; user.slots/score gespiegelt
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

    if not _in_challenge_window(act_date):
        return {"message": "Activity is outside challenge window (Nov 2025); ignored."}

    existing_claim = db.query(Claim).filter(
        Claim.user_id == user.id,
        Claim.date == act_date
    ).first()
    if existing_claim:
        return {"message": "User already has a claim for this date", "claim": {"km": existing_claim.km}}

    if activity.distance_km is None:
        return {"error": "Activity distance missing"}

    floor_km = int(activity.distance_km // 1)
    candidate_start = min(max(floor_km, 1), 30)

    monthly_claims = _current_month_claims(db, user.id)
    taken = {int(c.km) for c in monthly_claims if c.km is not None and 1 <= int(c.km) <= 30}

    assigned = None
    for k in range(candidate_start, 0, -1):
        if k not in taken:
            assigned = k
            break

    if not assigned:
        return {"message": "No available km to claim for this activity"}

    claim = Claim(user_id=user.id, km=assigned, date=act_date, activity_id=activity.id)
    db.add(claim)

    activity.status = "claimed"
    activity.effective_km = assigned
    db.add(activity)

    db.flush()
    monthly_claims = _current_month_claims(db, user.id)
    _rebuild_user_slots_and_score_from_claims(user, monthly_claims)
    db.add(user)

    db.commit()
    db.refresh(claim)
    return {"message": "Claim created", "km": assigned}


# -----------------------
# Endpoints
# -----------------------

@router.get("/")
def get_all_activities(db: Session = Depends(get_db)):
    return db.query(Activity).all()


@router.post("/process/{activity_id}")
def process_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    result = process_activity_instance(activity, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/process_by_strava/{strava_activity_id}")
def process_by_strava(
    strava_activity_id: int,
    owner_strava_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Holt eine bestimmte Aktivität direkt von Strava, legt sie an (falls fehlend) und processed sie.
    - Refresh bei 401 (wenn möglich), dann Retry
    - Nur Run/TrailRun/VirtualRun
    - Challenge nur November 2025
    """
    # Bereits vorhanden?
    existing = db.query(Activity).filter(Activity.strava_id == str(strava_activity_id)).first()
    if existing:
        result = process_activity_instance(existing, db)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result

    # Nutzer bestimmen
    if owner_strava_id is not None:
        user = db.query(User).filter(User.strava_id == owner_strava_id).first()
    else:
        user = db.query(User).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found (provide owner_strava_id if multiple users exist)")

    token = _ensure_valid_access_token(user)
    if not token:
        return {"status": "no_token", "message": "User has no access_token"}

    # 1. Versuch
    r = _strava_get(f"/activities/{strava_activity_id}", token)
    # Bei 401 versuchen zu refreshen & retry
    if r.status_code == 401:
        new_token = _refresh_token(user)
        if new_token:
            db.add(user)
            db.commit()
            token = new_token
            r = _strava_get(f"/activities/{strava_activity_id}", token)

    if r.status_code != 200:
        return {"status": "error_fetching_activity", "code": r.status_code, "text": r.text}

    data = r.json()

    if not _is_allowed_run_type(data.get("type")):
        return {"status": "ignored_non_run", "type": data.get("type"), "allowed": ["Run", "TrailRun", "VirtualRun"]}

    distance_m = data.get("distance", 0) or 0
    distance_km = float(distance_m) / 1000.0
    try:
        act_date = _parse_activity_date_from_payload(data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to parse date: {e}")

    # Nur Aktivitäten aus Nov 2025 aufnehmen
    if not _in_challenge_window(act_date):
        return {"message": "Activity is outside challenge window (Nov 2025); ignored."}

    # Activity anlegen
    try:
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to insert Activity: {e}")

    # Verarbeiten
    result = process_activity_instance(activity, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/sync_recent/{owner_strava_id}")
def sync_recent(owner_strava_id: int, db: Session = Depends(get_db)):
    """
    NOTFALL-SYNC (kein Webhook nötig):
    - Holt die letzten Aktivitäten des Nutzers (owner_strava_id) aus Strava.
    - Filtert auf Nov 2025 + Laufarten.
    - Legt fehlende Aktivitäten in DB an und processed sie sofort.
    - Gibt eine kurze Bilanz zurück.
    """
    user = db.query(User).filter(User.strava_id == owner_strava_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = _ensure_valid_access_token(user)
    if not token:
        return {"status": "no_token", "message": "User has no access_token"}

    # Zeitfenster auf Nov 2025 begrenzen (AFTER = UTC epoch)
    first_day, last_day = _month_bounds(CHALLENGE_YEAR, CHALLENGE_MONTH)
    after_epoch = int(datetime.datetime(first_day.year, first_day.month, first_day.day, 0, 0, 0, tzinfo=datetime.timezone.utc).timestamp())
    before_epoch = int(datetime.datetime(last_day.year, last_day.month, last_day.day, 23, 59, 59, tzinfo=datetime.timezone.utc).timestamp())

    params = {
        "per_page": 50,
        "page": 1,
        "after": after_epoch,
        "before": before_epoch,
    }

    # 1. Versuch
    r = _strava_get("/athlete/activities", token, params=params)
    if r.status_code == 401:
        new_token = _refresh_token(user)
        if new_token:
            db.add(user)
            db.commit()
            token = new_token
            r = _strava_get("/athlete/activities", token, params=params)

    if r.status_code != 200:
        return {"status": "error_fetching_activities", "code": r.status_code, "text": r.text}

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

        sid = str(it.get("id"))
        if not sid:
            skipped += 1
            continue

        # Distanz
        dist_km = float((it.get("distance", 0) or 0)) / 1000.0

        # existiert schon?
        existing = db.query(Activity).filter(Activity.strava_id == sid).first()
        if existing:
            # sicherheitshalber aktualisieren, falls Distanz/Datum leer war
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

        # neu anlegen
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

        res = process_activity_instance(activity, db)
        if res.get("message") == "Claim created":
            processed += 1
        else:
            skipped += 1

    return {
        "status": "ok",
        "owner_strava_id": owner_strava_id,
        "fetched": len(items),
        "created_in_db": created,
        "processed_claims": processed,
        "skipped": skipped
    }
