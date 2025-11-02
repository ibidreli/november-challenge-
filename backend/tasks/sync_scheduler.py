import asyncio
import datetime
from typing import Dict
import logging
from sqlalchemy.orm import Session
from database import SessionLocal
from models.user import User

logger = logging.getLogger(__name__)

# Tracking: {user_id: last_sync_timestamp}
_sync_tracker: Dict[int, float] = {}
SYNC_INTERVAL_SECONDS = 1800  # 30 minutes

def get_seconds_until_next_sync(user_id: int) -> int:
    """Berechne Sekunden bis zum nächsten Auto-Sync für einen User."""
    last_sync = _sync_tracker.get(user_id, 0)
    elapsed = datetime.datetime.now().timestamp() - last_sync
    remaining = max(0, SYNC_INTERVAL_SECONDS - elapsed)
    return int(remaining)

def mark_sync_done(user_id: int) -> None:
    """Markiere User als gerade synced."""
    _sync_tracker[user_id] = datetime.datetime.now().timestamp()

def should_sync_user(user_id: int) -> bool:
    """Prüfe ob User auto-synced werden soll (>30min seit letztem Sync)."""
    last_sync = _sync_tracker.get(user_id, 0)
    elapsed = datetime.datetime.now().timestamp() - last_sync
    return elapsed >= SYNC_INTERVAL_SECONDS

async def background_sync_loop() -> None:
    """
    Background-Task: Syncet alle User regelmäßig.
    Ruft sync_recent_internal() DIREKT auf (nicht via HTTP-Request um Timeouts zu vermeiden).
    Läuft kontinuierlich und checkt alle 30 Sekunden ob jemand synced werden muss.
    """
    # Import hier um zirkuläre Imports zu vermeiden
    from routes.activities import sync_recent_internal
    
    logger.info("Background sync loop started (interval: 30 min)")
    
    while True:
        try:
            db = SessionLocal()
            users = db.query(User).filter(User.strava_id.isnot(None)).all()
            logger.debug(f"Checking {len(users)} users for auto-sync")
            
            for user in users:
                if should_sync_user(user.id):
                    try:
                        logger.info(f"Auto-syncing user {user.id} (strava_id: {user.strava_id})")
                        
                        # ✅ DIREKT aufrufen (kein HTTP-Request!)
                        result = sync_recent_internal(user.strava_id, db)
                        
                        logger.info(f"Auto-sync user {user.id} completed: {result}")
                        mark_sync_done(user.id)
                    
                    except Exception as e:
                        logger.error(f"Auto-sync failed for user {user.id}: {e}", exc_info=True)
            
            db.close()
            await asyncio.sleep(30)  # Check alle 30 Sekunden
        
        except Exception as e:
            logger.error(f"Background sync loop error: {e}", exc_info=True)
            await asyncio.sleep(30)
