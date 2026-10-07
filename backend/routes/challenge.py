from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from services.challenge import configuration, statistics

router = APIRouter()
@router.get("")
@router.get("/", include_in_schema=False)
def challenge(db: Session = Depends(get_db)):
    return configuration(db)

@router.get("/statistics")
def stats(db: Session = Depends(get_db)):
    return statistics(db)
