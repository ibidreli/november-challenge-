import hmac
import os
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()

@router.get("/webhook")
def verify(mode: str = Query(alias="hub.mode"), challenge: str = Query(alias="hub.challenge"), token: str = Query(alias="hub.verify_token")):
    expected = os.getenv("STRAVA_WEBHOOK_VERIFY_TOKEN", "")
    if not expected or mode != "subscribe" or not hmac.compare_digest(token, expected):
        raise HTTPException(403, "Invalid webhook verification")
    return {"hub.challenge": challenge}

class Event(BaseModel):
    object_type: str
    object_id: int
    owner_id: int
    aspect_type: str
    subscription_id: int

@router.post("/webhook")
def webhook(event: Event, tasks: BackgroundTasks):
    expected = os.getenv("STRAVA_WEBHOOK_SUBSCRIPTION_ID", "")
    if not expected:
        raise HTTPException(503, "Webhook subscription is not configured")
    if str(event.subscription_id) != expected:
        raise HTTPException(403, "Unknown subscription")
    if event.object_type == "activity" and event.aspect_type in {"create", "update", "delete"}:
        from services.strava import webhook_background
        tasks.add_task(webhook_background, event.owner_id, event.object_id, event.aspect_type)
    return {"ok": True}
