"""Strava import, pagination, token rotation and webhook reconciliation."""
import logging
import os
import threading
from contextlib import contextmanager
from datetime import datetime, time, timedelta, timezone
from urllib.parse import urlsplit
import requests
from sqlalchemy import select, text
from database import SessionLocal, engine
from models.user import User
from models.activity import Activity
from services.challenge import edition, lock_user, rebuild_user
from services.time import utcnow, ZURICH
from services.schedule import bounds

log = logging.getLogger(__name__)
API = "https://www.strava.com/api/v3"
_locks, _locks_guard = {}, threading.Lock()

@contextmanager
def sync_lock(user_id):
    """Prevent overlapping imports across Render workers (and local threads)."""
    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            acquired = conn.scalar(text("SELECT pg_try_advisory_lock(202611, :uid)"), {"uid": user_id})
            conn.commit()
            try:
                yield acquired
            finally:
                if acquired:
                    conn.execute(text("SELECT pg_advisory_unlock(202611, :uid)"), {"uid": user_id})
                    conn.commit()
    else:
        with _locks_guard:
            guard = _locks.setdefault(user_id, threading.Lock())
        acquired = guard.acquire(blocking=False)
        try:
            yield acquired
        finally:
            if acquired:
                guard.release()

def access_token(db, user_id, force=False):
    user = db.scalar(select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True))
    if not user or not user.refresh_token:
        db.rollback()
        raise RuntimeError("Strava must be reconnected")
    if not force and user.access_token and user.token_expires_at and user.token_expires_at > int(utcnow().replace(tzinfo=timezone.utc).timestamp()) + 60:
        token = user.access_token
        db.commit()
        return token
    result = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": os.getenv("STRAVA_CLIENT_ID"), "client_secret": os.getenv("STRAVA_CLIENT_SECRET"),
        "grant_type": "refresh_token", "refresh_token": user.refresh_token}, timeout=20)
    if result.status_code in {400, 401}:
        try:
            revoked = any(error.get("field") == "refresh_token" for error in result.json().get("errors", []))
        except (ValueError, TypeError, AttributeError):
            revoked = False
        if revoked:
            user.access_token = user.refresh_token = user.token_expires_at = None
            db.commit()
    result.raise_for_status()
    data = result.json()
    user.access_token, user.refresh_token, user.token_expires_at = data["access_token"], data["refresh_token"], int(data["expires_at"])
    db.commit()  # release user lock before taking edition lock
    return user.access_token

def api_get(db, user_id, path, params=None):
    token = access_token(db, user_id)
    result = requests.get(API + path, params=params, headers={"Authorization": "Bearer " + token}, timeout=25)
    if result.status_code == 401:
        token = access_token(db, user_id, force=True)
        result = requests.get(API + path, params=params, headers={"Authorization": "Bearer " + token}, timeout=25)
    return result

def normalized(data):
    if data.get("sport_type", data.get("type")) not in {"Run", "TrailRun", "VirtualRun"}:
        return None
    raw = data.get("start_date")
    if raw:
        start = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
    else:
        start = datetime.fromisoformat(data["start_date_local"]).replace(tzinfo=ZURICH)
    meters = float(data["distance"])
    import math
    if not math.isfinite(meters) or meters < 0:
        raise ValueError("Invalid Strava distance")
    return {"strava_id": str(int(data["id"])), "date": start.astimezone(ZURICH).date(),
            "started_at": start.astimezone(timezone.utc).replace(tzinfo=None), "distance_km": meters / 1000}

def upsert(db, user_id, data):
    sid = str(int(data["id"]))
    existing = db.scalar(select(Activity).where(Activity.strava_id == sid))
    if existing and existing.user_id != user_id:
        raise ValueError("Activity owner mismatch")
    if existing and existing.status == "admin_excluded":
        return
    values = normalized(data)
    if values is None:
        if existing:
            existing.status, existing.effective_km = "not_run", 0
        return
    if not existing:
        existing = Activity(user_id=user_id, is_manual=False)
        db.add(existing)
    for key, value in values.items():
        setattr(existing, key, value)
    existing.status, existing.effective_km = "pending", 0

def sync_user(db, user_id):
    e = edition(db)
    first, last = bounds(db, e)
    db.commit()
    after = int(datetime.combine(first, time(), ZURICH).timestamp()) - 1
    before = int(datetime.combine(last + timedelta(days=1), time(), ZURICH).timestamp())
    fetched = []
    for page in range(1, 101):
        result = api_get(db, user_id, "/athlete/activities", {"after": after, "before": before, "per_page": 200, "page": page})
        result.raise_for_status()
        batch = result.json()
        if not isinstance(batch, list):
            raise ValueError("Invalid Strava activities response")
        fetched.extend(batch)
        if len(batch) < 200:
            break
    else:
        raise RuntimeError("Strava pagination limit exceeded; import was not committed")
    # Nothing has been written until the complete month has been fetched.
    e, user = lock_user(db, user_id)
    if bounds(db, e) != (first, last):
        raise RuntimeError("Challenge calendar changed during import; retry synchronization")
    seen = {str(int(a["id"])) for a in fetched}
    for data in fetched:
        upsert(db, user_id, data)
    for old in db.scalars(select(Activity).where(Activity.user_id == user_id, Activity.date >= first,
            Activity.date <= last, Activity.is_manual.is_(False), Activity.strava_id.is_not(None))).all():
        if old.strava_id not in seen and old.status != "admin_excluded":
            old.status, old.effective_km = "deleted", 0
    db.flush()
    rebuild_user(db, user_id, e)
    user.last_synced_at = utcnow()
    user.last_sync_attempt_at, user.last_sync_error = utcnow(), None
    db.commit()

def sync_user_background(user_id):
    if os.getenv("STRAVA_SYNC_ENABLED", "1") != "1":
        return
    with sync_lock(user_id) as acquired:
        if not acquired:
            return
        with SessionLocal() as db:
            try:
                sync_user(db, user_id)
            except Exception as exc:
                db.rollback()
                # Never log credential-bearing request/response bodies.
                if isinstance(exc, requests.HTTPError) and exc.response is not None:
                    # Log only status and endpoint: query strings, bodies and headers can contain credentials.
                    log.warning("Strava sync failed for user %s (HTTPError status=%s endpoint=%s)",
                                user_id, exc.response.status_code, urlsplit(exc.response.url or "").path)
                else:
                    log.warning("Strava sync failed for user %s (%s)", user_id, type(exc).__name__)
                user = db.get(User, user_id)
                if user:
                    user.last_sync_attempt_at = utcnow()  # bounded retry frequency on failures
                    status = exc.response.status_code if isinstance(exc, requests.HTTPError) and exc.response is not None else None
                    user.last_sync_error = {
                        401: "Strava hat den Zugriff abgelehnt. Bitte Strava erneut verbinden.",
                        403: "Strava erlaubt den Aktivitätszugriff nicht. Bitte erneut verbinden und die Lauf-Freigabe erlauben.",
                        429: "Das Strava-Anfragelimit ist erreicht. Bitte später erneut synchronisieren.",
                    }.get(status, "Strava konnte nicht synchronisiert werden. Bitte später erneut versuchen.")
                    db.commit()

def sync_all_background(due_only=False):
    if os.getenv("STRAVA_SYNC_ENABLED", "1") != "1":
        return
    with SessionLocal() as db:
        query = select(User.id).where(User.refresh_token.is_not(None))
        if due_only:
            query = query.where((User.last_sync_attempt_at.is_(None)) | (User.last_sync_attempt_at < utcnow() - timedelta(minutes=30)))
        ids = db.scalars(query).all()
    for uid in ids:
        sync_user_background(uid)

def webhook_background(owner_id, activity_id, aspect):
    if os.getenv("STRAVA_SYNC_ENABLED", "1") != "1":
        return
    with SessionLocal() as db:
        uid = db.scalar(select(User.id).where(User.strava_id == owner_id))
    if not uid:
        return
    with sync_lock(uid) as acquired:
        if not acquired:
            return  # scheduled full sync also reconciles edits/deletes
        with SessionLocal() as db:
            try:
                response = api_get(db, uid, f"/activities/{activity_id}")
                if response.status_code == 404:
                    e, _ = lock_user(db, uid)
                    a = db.scalar(select(Activity).where(Activity.strava_id == str(activity_id), Activity.user_id == uid))
                    if a and a.status != "admin_excluded":
                        a.status, a.effective_km = "deleted", 0
                        db.flush()
                        rebuild_user(db, uid, e)
                        db.commit()
                    return
                response.raise_for_status()
                data = response.json()
                if int(data.get("athlete", {}).get("id", 0)) != owner_id or int(data["id"]) != activity_id:
                    raise ValueError("Webhook activity owner mismatch")
                e, _ = lock_user(db, uid)
                upsert(db, uid, data)
                db.flush()
                rebuild_user(db, uid, e)
                db.commit()
            except Exception as exc:
                db.rollback()
                log.warning("Webhook import failed for user %s (%s)", uid, type(exc).__name__)
