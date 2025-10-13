from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.user import User
from database import SessionLocal


router = APIRouter()


@router.get("/me")
def get_current_user(db: Session = Depends(SessionLocal)):
    user = db.query(User).first()
    if not user:
        return {"message": "No users found."}
    return {"name": user.name, "strava_id": user.strava_id, "total_score": user.total_score}