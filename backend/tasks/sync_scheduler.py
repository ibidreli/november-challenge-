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
SYNC_INTERVAL_SECONDS = 900  # 15 minutes

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
    """Prüfe ob User auto-synced werden soll (>15min seit letztem Sync)."""
    last_sync = _sync_tracker.get(user_id, 0)
    elapsed = datetime.datetime.now().timestamp() - last_sync
    return elapsed >= SYNC_INTERVAL_SECONDS

async def background_sync_loop() -> None:
    """
    Background-Task: Syncet alle User regelmäßig via POST Endpoint.
    Läuft kontinuierlich und checkt alle 30 Sekunden ob jemand synced werden muss.
    """
    import requests
    
    logger.info("Background sync loop started (interval: 15 min)")
    
    while True:
        try:
            db = SessionLocal()
            users = db.query(User).filter(User.strava_id.isnot(None)).all()
            logger.debug(f"Checking {len(users)} users for auto-sync")
            
            for user in users:
                if should_sync_user(user.id):
                    try:
                        logger.info(f"Auto-syncing user {user.id} (strava_id: {user.strava_id})")
                        
                        # Rufe den bestehenden POST Endpoint auf
                        # WICHTIG: Verwende localhost oder deine echte Domain
                        base_url = "https://november-challenge.onrender.com"  # oder deine render-domain
                        response = requests.post(
                            f"{base_url}/activities/sync_recent/{user.strava_id}",
                            timeout=60
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            logger.info(f"Auto-sync user {user.id} completed: {result}")
                            mark_sync_done(user.id)
                        else:
                            logger.warning(f"Auto-sync user {user.id} failed: {response.status_code}")
                            # Mark as attempted anyway to avoid hammering
                            mark_sync_done(user.id)
                    
                    except Exception as e:
                        logger.error(f"Auto-sync failed for user {user.id}: {e}", exc_info=True)
            
            db.close()
            await asyncio.sleep(30)  # Check alle 30 Sekunden
        
        except Exception as e:
            logger.error(f"Background sync loop error: {e}", exc_info=True)
            await asyncio.sleep(30)
