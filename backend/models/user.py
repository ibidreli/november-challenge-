from sqlalchemy import Column, Integer, String, JSON, BigInteger, DateTime
from database import Base
from sqlalchemy.ext.mutable import MutableList
# mark modifications
from sqlalchemy.orm.attributes import flag_modified


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    strava_id = Column(BigInteger, unique=True, nullable=True)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    token_expires_at = Column(BigInteger, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    last_sync_attempt_at = Column(DateTime, nullable=True)
    last_sync_error = Column(String(120), nullable=True)
    total_score = Column(Integer, default=0)
    # slots: JSON list with 30 entries. Use MutableList so in-place mutations are tracked by SQLAlchemy.
    # use a callable default to avoid sharing the same list instance across rows
    slots = Column(MutableList.as_mutable(JSON), nullable=False, default=lambda: [None] * 30)

    def ensure_slots(self):
        # make sure slots is a 30-length list
        try:
            if not isinstance(self.slots, list):
                self.slots = [None] * 30
                flag_modified(self, "slots")
            elif len(self.slots) < 30:
                self.slots = (self.slots or []) + [None] * (30 - len(self.slots))
                flag_modified(self, "slots")
            elif len(self.slots) > 30:
                self.slots = self.slots[:30]
                flag_modified(self, "slots")
        except Exception:
            self.slots = [None] * 30
            flag_modified(self, "slots")
