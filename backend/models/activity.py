from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base


class Activity(Base):
    __tablename__ = "activities"


    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    strava_id = Column(String, unique=True, nullable=True)
    date = Column(Date)
    distance_km = Column(Float)
    effective_km = Column(Integer)
    status = Column(String, default="pending")
    is_manual = Column(Boolean, default=False)  # NEW: True = manuelle Eingabe, nicht von Strava


    user = relationship("User", backref="activities")