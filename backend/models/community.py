from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, UniqueConstraint, CheckConstraint
from database import Base

class CommunityRun(Base):
    __tablename__ = "community_runs"
    id = Column(String(32), primary_key=True)
    creator_name = Column(String(60), nullable=False)
    creator_identity = Column(String(64), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    distance_km = Column(Float, nullable=False)
    pace_seconds = Column(Integer, nullable=False)
    starts_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    meeting_point = Column(String(160), nullable=False)
    cancelled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False)
    __table_args__ = (CheckConstraint("distance_km > 0"),)

class CommunityParticipant(Base):
    __tablename__ = "community_participants"
    id = Column(String(32), primary_key=True)
    run_id = Column(String(32), ForeignKey("community_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(60), nullable=False)
    identity_hash = Column(String(64), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    __table_args__ = (UniqueConstraint("run_id", "identity_hash"), UniqueConstraint("run_id", "user_id"),)

class RequestLimit(Base):
    __tablename__ = "request_limits"
    key = Column(String(64), primary_key=True)
    window = Column(Integer, primary_key=True)
    count = Column(Integer, nullable=False)
