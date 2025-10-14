from sqlalchemy import Column, Integer, String, DateTime, Float, JSON
from database import Base
import math


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    strava_id = Column(Integer, unique=True, nullable=True)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    total_score = Column(Integer, default=0)
    # slots: JSON list with 30 entries. Each entry is None or {"km": int, "activity_id": int}
    slots = Column(JSON, nullable=False, default=[None]*30)

    def ensure_slots(self):
        # make sure slots is a 30-length list
        try:
            if not isinstance(self.slots, list):
                self.slots = [None] * 30
            elif len(self.slots) < 30:
                self.slots = (self.slots or []) + [None] * (30 - len(self.slots))
            elif len(self.slots) > 30:
                self.slots = self.slots[:30]
        except Exception:
            self.slots = [None] * 30

    def assign_activity(self, distance_km: float, activity_id: int):
        """
        Versuche, einen Slot zu setzen:
        - Start bei floor(distance_km)
        - Suche abwärts nach dem ersten freien Slot (>=1)
        - Setze slot (index = km-1) = {"km": km, "activity_id": activity_id}
        - Addiere km als Punkte zu total_score
        - Gibt (assigned_km) oder None zurück
        """
        self.ensure_slots()
        km = int(math.floor(distance_km))
        if km < 1:
            return None
        for cand in range(km, 0, -1):
            idx = cand - 1
            if idx < 30 and self.slots[idx] is None:
                self.slots[idx] = {"km": cand, "activity_id": activity_id}
                try:
                    self.total_score = (self.total_score or 0) + cand
                except Exception:
                    self.total_score = cand
                return cand
        return None