from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
import os, requests

router = APIRouter()

STRAVA_API_BASE = "https://www.strava.com/api/v3/activities/"

@router.get("/webhook")
async def verify_challenge(request: Request):
    params = dict(request.query_params)
    if "hub.challenge" in params:
        return PlainTextResponse(params["hub.challenge"])
    return JSONResponse({"status": "ok"})

@router.post("/webhook")
async def handle_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    obj_type = payload.get("object_type")
    aspect = payload.get("aspect_type")
    owner_id = payload.get("owner_id")
    object_id = payload.get("object_id")

    if obj_type != "activity" or object_id is None or owner_id is None:
        return JSONResponse({"status": "ignored"})

    user = db.query(User).filter_by(strava_id=owner_id).first()
    if not user:
        return JSONResponse({"status": "user_not_found", "owner_id": owner_id})

    access_token = user.access_token
    if not access_token:
        return JSONResponse({"status": "no_token", "user_id": user.id})

    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        r = requests.get(STRAVA_API_BASE + str(object_id), headers=headers, timeout=10)
        if r.status_code != 200:
            return JSONResponse({"status": "error_fetching_activity", "code": r.status_code}, status_code=502)
        data = r.json()
        distance_m = data.get("distance", 0)
        distance_km = (distance_m or 0) / 1000.0
    except Exception as e:
        return JSONResponse({"status": "fetch_error", "error": str(e)}, status_code=502)

    assigned = user.assign_activity(distance_km, int(object_id))
    user.ensure_slots()
    db.add(user)
    db.commit()

    return JSONResponse({"status": "ok", "assigned_km": assigned, "total_score": user.total_score})
