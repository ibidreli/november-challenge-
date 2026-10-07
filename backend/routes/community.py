import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy import select, or_, false
from sqlalchemy.orm import Session
from database import get_db
from models.community import CommunityRun, CommunityParticipant
from services.sessions import optional_user, guest_identity
from services.time import utcnow, iso_utc
from services.limits import limit

router = APIRouter()

class Name(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    @field_validator("name")
    @classmethod
    def clean(cls, value):
        value = " ".join(value.split())
        if not value:
            raise ValueError("Bitte einen Namen eingeben.")
        return value

class RunBody(Name):
    model_config = ConfigDict(allow_inf_nan=False)
    distance_km: float = Field(gt=0, le=300)
    pace_seconds: int = Field(ge=60, le=1800)
    starts_at: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    meeting_point: str = Field(min_length=1, max_length=160)
    @field_validator("starts_at")
    @classmethod
    def aware(cls, value):
        if not value.tzinfo:
            raise ValueError("Startzeit muss eine Zeitzone enthalten.")
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    @field_validator("meeting_point")
    @classmethod
    def place(cls, value):
        if not value.strip():
            raise ValueError("Bitte den Treffpunkt kurz beschreiben.")
        return value.strip()

def active(db, run_id, lock=False):
    query = select(CommunityRun).where(CommunityRun.id == run_id, CommunityRun.cancelled.is_(False), CommunityRun.expires_at > utcnow())
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    r = db.scalar(query)
    if not r:
        raise HTTPException(404, "Dieser Lauf ist nicht mehr verfügbar.")
    return r

def owns(r, identity, user):
    return r.creator_identity == identity or bool(user and r.user_id == user.id)

def own_participant(db, run_id, identity, user):
    return db.scalar(select(CommunityParticipant).where(CommunityParticipant.run_id == run_id,
        or_(CommunityParticipant.identity_hash == identity, CommunityParticipant.user_id == user.id if user else false())))

def serialize(db, r, identity, user):
    people = db.scalars(select(CommunityParticipant).where(CommunityParticipant.run_id == r.id)).all()
    people.sort(key=lambda p: (p.identity_hash != r.creator_identity, p.name.casefold(), p.id))
    joined = any(p.identity_hash == identity or (user and p.user_id == user.id) for p in people)
    owner = owns(r, identity, user)
    # Expose names, never browser identity hashes, Strava IDs or account IDs.
    return {"id": r.id, "creator_name": r.creator_name, "distance_km": r.distance_km,
            "pace_seconds": r.pace_seconds, "starts_at": iso_utc(r.starts_at), "expires_at": iso_utc(r.expires_at),
            "latitude": r.latitude, "longitude": r.longitude, "meeting_point": r.meeting_point,
            "participants": [p.name for p in people], "joined": bool(joined), "can_manage": owner,
            "can_leave": bool(joined and not owner)}

@router.get("")
@router.get("/", include_in_schema=False)
def runs(request: Request, response: Response, user=Depends(optional_user), db: Session = Depends(get_db)):
    identity = guest_identity(request, response)
    records = db.scalars(select(CommunityRun).where(CommunityRun.cancelled.is_(False), CommunityRun.expires_at > utcnow())
                         .order_by(CommunityRun.starts_at).limit(200)).all()
    return {"server_now": iso_utc(utcnow()), "runs": [serialize(db, r, identity, user) for r in records]}

@router.post("", status_code=201)
def create(body: RunBody, request: Request, response: Response, user=Depends(optional_user), db: Session = Depends(get_db)):
    limit(db, request, "create_run", 5)
    if body.starts_at <= utcnow() or body.starts_at > utcnow() + timedelta(days=366):
        raise HTTPException(422, "Die Startzeit muss in der Zukunft und innerhalb eines Jahres liegen.")
    identity = guest_identity(request, response)
    values = body.model_dump(exclude={"name"})
    r = CommunityRun(id=uuid.uuid4().hex, creator_name=body.name, creator_identity=identity,
                     user_id=user.id if user else None, expires_at=body.starts_at + timedelta(hours=3), created_at=utcnow(), **values)
    db.add(r)
    db.flush()
    db.add(CommunityParticipant(id=uuid.uuid4().hex, run_id=r.id, name=body.name, identity_hash=identity, user_id=user.id if user else None))
    db.commit()
    return serialize(db, r, identity, user)

@router.put("/{run_id}")
def edit(run_id: str, body: RunBody, request: Request, response: Response, user=Depends(optional_user), db: Session = Depends(get_db)):
    identity = guest_identity(request, response)
    r = active(db, run_id, lock=True)
    if not owns(r, identity, user):
        raise HTTPException(403, "Nur der Ersteller kann diesen Lauf ändern.")
    if r.starts_at <= utcnow():
        raise HTTPException(409, "Der Lauf hat bereits begonnen.")
    if body.starts_at <= utcnow() or body.starts_at > utcnow() + timedelta(days=366):
        raise HTTPException(422, "Bitte eine zukünftige Startzeit innerhalb eines Jahres wählen.")
    p = db.scalar(select(CommunityParticipant).where(CommunityParticipant.run_id == r.id, CommunityParticipant.identity_hash == r.creator_identity))
    if p:
        p.name = body.name
    for key, value in body.model_dump(exclude={"name"}).items():
        setattr(r, key, value)
    r.creator_name, r.expires_at = body.name, body.starts_at + timedelta(hours=3)
    db.commit()
    return serialize(db, r, identity, user)

@router.delete("/{run_id}")
def cancel(run_id: str, request: Request, response: Response, user=Depends(optional_user), db: Session = Depends(get_db)):
    identity = guest_identity(request, response)
    r = active(db, run_id, lock=True)
    if not owns(r, identity, user):
        raise HTTPException(403, "Nur der Ersteller kann diesen Lauf absagen.")
    r.cancelled = True
    db.commit()
    return {"ok": True}

@router.post("/{run_id}/participants")
def join(run_id: str, body: Name, request: Request, response: Response, user=Depends(optional_user), db: Session = Depends(get_db)):
    limit(db, request, "join_run", 60)
    identity = guest_identity(request, response)
    r = active(db, run_id, lock=True)
    if not own_participant(db, run_id, identity, user):
        db.add(CommunityParticipant(id=uuid.uuid4().hex, run_id=run_id, name=body.name, identity_hash=identity, user_id=user.id if user else None))
    db.commit()
    return serialize(db, r, identity, user)

@router.delete("/{run_id}/participants/me")
def leave(run_id: str, request: Request, response: Response, user=Depends(optional_user), db: Session = Depends(get_db)):
    identity = guest_identity(request, response)
    r = active(db, run_id, lock=True)
    if owns(r, identity, user):
        raise HTTPException(409, "Als Ersteller kannst du den Lauf absagen.")
    p = own_participant(db, run_id, identity, user)
    if p:
        db.delete(p)
        db.commit()
    return serialize(db, r, identity, user)
