"""Disposable local server exclusively for Playwright. Never use for deployment."""
import os
import sys
import tempfile
from pathlib import Path
from datetime import date, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
temporary = tempfile.TemporaryDirectory(prefix="november-e2e-")
os.environ.update(DATABASE_URL="sqlite:///" + str(Path(temporary.name) / "e2e.db"), ADMIN_PASSWORD="e2e-only-password",
    CHALLENGE_YEAR="2026", LOAD_ENV_FILE="0", REQUIRE_POSTGRES="0", ENABLE_BACKGROUND_SYNC="0", COOKIE_SECURE="0",
    FRONTEND_URL="http://localhost:5179", STRAVA_CLIENT_ID="", STRAVA_CLIENT_SECRET="")
import main
from database import SessionLocal
from models.user import User
from models.activity import Activity
from models.session import AuthSession
from services import challenge
from services.time import utcnow
from services.sessions import digest
import routes.admin
challenge.local_today = lambda: date(2026, 11, 4)
routes.admin.local_today = lambda: date(2026, 11, 4)
if not main.DB_AVAILABLE:
    raise RuntimeError("E2E backend did not initialize")
with SessionLocal() as db:
    challenge.save_draw(db, 1, [5, 6, 9, 14, 19, 24, 27, 29], publish=True)
    u = User(name="Sofia Integration", strava_id=99)
    db.add(u); db.flush()
    for day, km in [(1, 35), (2, 30), (3, 7)]:
        db.add(Activity(user_id=u.id, date=date(2026, 11, day), distance_km=km, is_manual=False, status="pending"))
    db.add(AuthSession(token_hash=digest("e2e-user-session"), kind="user", user_id=u.id, expires_at=utcnow() + timedelta(days=1)))
    db.flush(); challenge.rebuild_user(db, u.id); db.commit()
if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run(main.app, host="127.0.0.1", port=8021, log_level="warning")
    finally:
        from database import engine
        engine.dispose(); temporary.cleanup()
