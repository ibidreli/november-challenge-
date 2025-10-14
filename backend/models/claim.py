from sqlalchemy import Column, Integer, Date, ForeignKey, DateTime
from sqlalchemy.sql import func
from database import Base

class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    km = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
