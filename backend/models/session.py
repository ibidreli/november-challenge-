from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from database import Base

class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash = Column(String(64), primary_key=True)
    kind = Column(String(10), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)

class OAuthState(Base):
    __tablename__ = "oauth_states"
    token_hash = Column(String(64), primary_key=True)
    return_to = Column(String(500), nullable=False)
    expires_at = Column(DateTime, nullable=False)
