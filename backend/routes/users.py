from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session
from database import get_db
from services.challenge import participant, leaderboard
from services.sessions import require_user
from services.limits import limit

router = APIRouter()

@router.get("/me")
def me(user=Depends(require_user), db: Session = Depends(get_db)):
    return participant(db, user, personal=True)

@router.get("/")
def users(db: Session = Depends(get_db)):
    return leaderboard(db)

@router.post("/me/sync", status_code=202)
def sync(request: Request, tasks: BackgroundTasks, user=Depends(require_user), db: Session = Depends(get_db)):
    limit(db, request, "personal_sync", 6)
    from services.strava import sync_user_background
    tasks.add_task(sync_user_background, user.id)
    return {"queued": True}
