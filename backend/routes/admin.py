import hmac
import os
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field, StrictInt, ConfigDict
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.activity import Activity
from models.claim import Claim
from models.challenge import ChallengeClaim
from models.session import AuthSession
from models.community import CommunityRun
from services.challenge import configuration, save_draw, set_finale, participant, edition, rebuild_user, lock_user, set_test_calendar
from services.schedule import bounds
from services.sessions import verify_admin_token, issue_session
from services.limits import limit
from services.time import local_today

router = APIRouter()

class Login(BaseModel):
    password: str = Field(max_length=500)

@router.post("/login")
def login(body: Login, request: Request, db: Session = Depends(get_db)):
    limit(db, request, "admin_login", 20)
    password = os.getenv("ADMIN_PASSWORD", "")
    if not password:
        raise HTTPException(503, "ADMIN_PASSWORD ist nicht gesetzt.")
    if not hmac.compare_digest(body.password.encode(), password.encode()):
        raise HTTPException(401, "Passwort ist falsch.")
    token = issue_session(db, kind="admin", days=2 / 24)
    db.commit()
    return {"token": token, "expires_in": 7200}

@router.post("/logout")
def logout(session=Depends(verify_admin_token), db: Session = Depends(get_db)):
    db.delete(session)
    db.commit()
    return {"ok": True}

@router.get("/challenge", dependencies=[Depends(verify_admin_token)])
def challenge(db: Session = Depends(get_db)):
    return configuration(db, admin=True)

class Draw(BaseModel):
    distances: list[StrictInt]

@router.put("/challenge/periods/{number}", dependencies=[Depends(verify_admin_token)])
def draft(number: int, body: Draw, db: Session = Depends(get_db)):
    return save_draw(db, number, body.distances)

@router.post("/challenge/periods/{number}/publish", dependencies=[Depends(verify_admin_token)])
def publish(number: int, body: Draw, db: Session = Depends(get_db)):
    return save_draw(db, number, body.distances, publish=True)

class Finale(BaseModel):
    km: StrictInt = Field(ge=1, le=30)

@router.put("/challenge/finale", dependencies=[Depends(verify_admin_token)])
def finale(body: Finale, db: Session = Depends(get_db)):
    return set_finale(db, body.km)

class TestCalendar(BaseModel):
    starts_on: date
    period_days: list[StrictInt] = Field(min_length=4, max_length=4)

@router.put("/challenge/test-calendar", dependencies=[Depends(verify_admin_token)])
def test_calendar(body: TestCalendar, db: Session = Depends(get_db)):
    return set_test_calendar(db, body.starts_on, body.period_days)

@router.get("/users", dependencies=[Depends(verify_admin_token)])
def users(db: Session = Depends(get_db)):
    return [{**participant(db, u, personal=True), "strava_id": u.strava_id} for u in db.query(User).order_by(User.name).all()]

class UserBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)

@router.post("/users", dependencies=[Depends(verify_admin_token)])
def create_user(body: UserBody, db: Session = Depends(get_db)):
    edition(db, lock=True)
    if not body.name.strip():
        raise HTTPException(422, "Bitte einen Namen eingeben.")
    u = User(name=body.name.strip())
    db.add(u)
    db.commit()
    return participant(db, u, personal=True)

@router.put("/users/{user_id}", dependencies=[Depends(verify_admin_token)])
def update_user(user_id: int, body: UserBody, db: Session = Depends(get_db)):
    _, u = lock_user(db, user_id)
    if not body.name.strip():
        raise HTTPException(422, "Bitte einen Namen eingeben.")
    u.name = body.name.strip()
    db.commit()
    return participant(db, u, personal=True)

@router.delete("/users/{user_id}", dependencies=[Depends(verify_admin_token)])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    _, u = lock_user(db, user_id)
    db.query(ChallengeClaim).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(Claim).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.query(Activity).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.delete(u)
    db.commit()
    return {"ok": True}

class ActivityBody(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    user_id: int
    date: date
    distance_km: float = Field(gt=0, le=300)

@router.get("/activities", dependencies=[Depends(verify_admin_token)])
def activities(user_id: int | None = None, db: Session = Depends(get_db)):
    e = edition(db)
    first, last = bounds(db, e)
    query = db.query(Activity).filter(Activity.date >= first, Activity.date <= last)
    if user_id:
        query = query.filter_by(user_id=user_id)
    return [{"id": a.id, "user_id": a.user_id, "date": a.date, "distance_km": a.distance_km,
             "effective_km": a.effective_km, "status": a.status, "is_manual": bool(a.is_manual)}
            for a in query.order_by(Activity.date.desc(), Activity.id.desc()).limit(1000).all()]

@router.post("/activities", dependencies=[Depends(verify_admin_token)])
def create_activity(body: ActivityBody, db: Session = Depends(get_db)):
    e, _ = lock_user(db, body.user_id)
    if body.date > local_today():
        raise HTTPException(422, "Läufe können erst nach dem Lauftag erfasst werden.")
    first, last = bounds(db, e)
    if not first <= body.date <= last:
        raise HTTPException(422, "Das Laufdatum muss innerhalb des Challenge-Zeitraums liegen.")
    a = Activity(**body.model_dump(), is_manual=True, status="pending")
    db.add(a)
    db.flush()
    rebuild_user(db, body.user_id, e)
    db.commit()
    return {"id": a.id, "effective_km": a.effective_km}

@router.put("/activities/{activity_id}", dependencies=[Depends(verify_admin_token)])
def update_activity(activity_id: int, body: ActivityBody, db: Session = Depends(get_db)):
    e = edition(db, lock=True)
    a = db.get(Activity, activity_id)
    if not a:
        raise HTTPException(404, "Aktivität nicht gefunden.")
    if not a.is_manual:
        raise HTTPException(409, "Strava-Läufe in Strava ändern oder eine manuelle Tageskorrektur erfassen.")
    if body.date > local_today():
        raise HTTPException(422, "Das Laufdatum liegt in der Zukunft.")
    old_id = a.user_id
    lock_user(db, body.user_id, e)
    for key, value in body.model_dump().items():
        setattr(a, key, value)
    a.status, a.effective_km = "pending", 0
    db.flush()
    for uid in sorted({old_id, body.user_id}):
        rebuild_user(db, uid, e)
    db.commit()
    return {"ok": True}

@router.delete("/activities/{activity_id}", dependencies=[Depends(verify_admin_token)])
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    e = edition(db, lock=True)
    a = db.get(Activity, activity_id)
    if not a:
        raise HTTPException(404, "Aktivität nicht gefunden.")
    # Keep raw history and the Strava ID; a deleted item cannot silently reappear on sync.
    a.status = "admin_excluded"
    db.flush()
    rebuild_user(db, a.user_id, e)
    db.commit()
    return {"ok": True}

@router.post("/activities/{activity_id}/restore", dependencies=[Depends(verify_admin_token)])
def restore_activity(activity_id: int, db: Session = Depends(get_db)):
    e = edition(db, lock=True)
    a = db.get(Activity, activity_id)
    if not a:
        raise HTTPException(404, "Aktivität nicht gefunden.")
    if a.status != "admin_excluded":
        raise HTTPException(409, "Diese Aktivität wurde nicht vom Admin ausgeschlossen.")
    a.status = "pending"
    db.flush()
    rebuild_user(db, a.user_id, e)
    db.commit()
    return {"ok": True}

@router.post("/sync", status_code=202, dependencies=[Depends(verify_admin_token)])
def sync(tasks: BackgroundTasks):
    if os.getenv("STRAVA_SYNC_ENABLED", "1") != "1":
        raise HTTPException(409, "Die Strava-Synchronisierung ist auf dieser Seite vorübergehend pausiert.")
    from services.strava import sync_all_background
    tasks.add_task(sync_all_background)
    return {"queued": True}

@router.get("/community", dependencies=[Depends(verify_admin_token)])
def community(db: Session = Depends(get_db)):
    from services.time import utcnow
    return [{"id": r.id, "name": r.creator_name, "starts_at": r.starts_at, "meeting_point": r.meeting_point}
            for r in db.query(CommunityRun).filter(CommunityRun.expires_at > utcnow(), CommunityRun.cancelled.is_(False)).all()]

@router.delete("/community/{run_id}", dependencies=[Depends(verify_admin_token)])
def moderate_run(run_id: str, db: Session = Depends(get_db)):
    r = db.get(CommunityRun, run_id)
    if not r:
        raise HTTPException(404, "Lauf nicht gefunden.")
    r.cancelled = True
    db.commit()
    return {"ok": True}
