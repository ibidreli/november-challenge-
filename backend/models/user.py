from sqlalchemy import Column, Integer, String, DateTime, Float
from database import Base


class User(Base):
    __tablename__ = "users"


    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    strava_id = Column(String, unique=True, index=True)
    access_token = Column(String)
    refresh_token = Column(String)
    token_expires_at = Column(DateTime)
    total_score = Column(Float, default=0.0)