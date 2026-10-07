from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, JSON, UniqueConstraint, CheckConstraint, Boolean, false
from database import Base

class ChallengeEdition(Base):
    __tablename__ = "challenge_editions"
    id = Column(Integer, primary_key=True)
    year = Column(Integer, unique=True, nullable=False)
    timezone = Column(String(50), nullable=False, default="Europe/Zurich")
    finale_km = Column(Integer, nullable=False, default=15)
    is_test = Column(Boolean, nullable=False, default=False, server_default=false())
    finale_on = Column(Date, nullable=True)

class ChallengePeriod(Base):
    __tablename__ = "challenge_periods"
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey("challenge_editions.id"), nullable=False)
    number = Column(Integer, nullable=False)
    starts_on = Column(Date, nullable=False)
    ends_on = Column(Date, nullable=False)
    draw_on = Column(Date, nullable=False)
    capacity = Column(Integer, nullable=False)
    draft_distances = Column(JSON, nullable=False, default=list)
    published_at = Column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint("edition_id", "number"),)

class DistanceTarget(Base):
    __tablename__ = "distance_targets"
    id = Column(Integer, primary_key=True)
    edition_id = Column(Integer, ForeignKey("challenge_editions.id"), nullable=False)
    period_id = Column(Integer, ForeignKey("challenge_periods.id"), nullable=True)
    km = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("edition_id", "km"), CheckConstraint("km BETWEEN 1 AND 30"),)

class ChallengeClaim(Base):
    __tablename__ = "challenge_claims"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    edition_id = Column(Integer, ForeignKey("challenge_editions.id"), nullable=False, index=True)
    target_id = Column(Integer, ForeignKey("distance_targets.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    date = Column(Date, nullable=False)
    km = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "edition_id", "date"), UniqueConstraint("user_id", "target_id"), UniqueConstraint("edition_id", "activity_id"),)
