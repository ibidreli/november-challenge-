from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.activity import Activity
from database import SessionLocal


router = APIRouter()


@router.get("/")
def get_all_activities(db: Session = Depends(SessionLocal)):
    return db.query(Activity).all()