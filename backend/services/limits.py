import time
from fastapi import HTTPException
from sqlalchemy import delete
from models.community import RequestLimit
from services.sessions import digest

def limit(db, request, scope, maximum, seconds=3600):
    """Atomic across workers; only the rate-limit transaction is committed here."""
    window = int(time.time()) // seconds
    key = digest(scope + ":" + (request.client.host if request.client else "unknown"))
    if db.bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    statement = insert(RequestLimit).values(key=key, window=window, count=1)
    statement = statement.on_conflict_do_update(index_elements=["key", "window"],
        set_={"count": RequestLimit.count + 1}, where=RequestLimit.count < maximum).returning(RequestLimit.count)
    result = db.execute(statement).first()
    db.execute(delete(RequestLimit).where(RequestLimit.window < window - 48))
    db.commit()
    if not result:
        raise HTTPException(429, "Zu viele Versuche. Bitte später erneut versuchen.")
