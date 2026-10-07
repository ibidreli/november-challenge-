import asyncio
import logging

async def background_sync_loop():
    from services.strava import sync_all_background
    while True:
        try:
            await asyncio.to_thread(sync_all_background, True)
        except Exception as exc:
            logging.getLogger(__name__).warning("Background sync failed (%s)", type(exc).__name__)
        await asyncio.sleep(30)
