from sqlalchemy import Column, Integer, String, DateTime, Float, JSON
from database import Base
import math
from sqlalchemy.ext.mutable import MutableList
# mark modifications
from sqlalchemy.orm.attributes import flag_modified


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    strava_id = Column(Integer, unique=True, nullable=True)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
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

    def assign_activity(self, distance_km: float, activity_id: int):
        """
        Atomar: kopiere slots, setze den slot, ersetze self.slots und markiere Änderung.
        FIX: Speichere nur integers in slots, nicht dicts
        """
        self.ensure_slots()
        km = int(math.floor(distance_km))
        if km < 1:
            return None
        # work on a copy to ensure SQLAlchemy notices the assignment
        current = list(self.slots or [None] * 30)
        for cand in range(km, 0, -1):
            idx = cand - 1
            if idx < 30 and (current[idx] is None):
                # FIX: Speichere nur integer, nicht dict
                current[idx] = cand
                # replace whole list and flag as modified
                self.slots = current
                try:
                    flag_modified(self, "slots")
                except Exception:
                    pass
                try:
                    self.total_score = (self.total_score or 0) + cand
                except Exception:
                    self.total_score = cand
                return cand
        return None