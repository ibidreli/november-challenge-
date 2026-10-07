from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ZURICH = ZoneInfo("Europe/Zurich")
def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)
def local_today():
    return datetime.now(ZURICH).date()
def iso_utc(value):
    return value.isoformat() + "Z" if value else None
