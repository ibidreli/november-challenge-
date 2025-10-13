

from fastapi import APIRouter, Depends, HTTPException
import requests, os, datetime
from database import SessionLocal
from models.user import User


router = APIRouter()


STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI", "http://localhost:8000/auth/callback")


@router.get("/login")
def strava_login():
    url = (
    f"https://www.strava.com/oauth/authorize?client_id={STRAVA_CLIENT_ID}"
    f"&response_type=code&redirect_uri={REDIRECT_URI}&scope=activity:read_all"
    )
    return {"auth_url": url}


@router.get("/callback")
def strava_callback(code: str, db: SessionLocal = Depends()):
    token_url = "https://www.strava.com/oauth/token"
    data = {
    "client_id": STRAVA_CLIENT_ID,
    "client_secret": STRAVA_CLIENT_SECRET,
    "code": code,
    "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to authenticate with Strava")


    tokens = response.json()
    athlete = tokens.get("athlete", {})


    user = db.query(User).filter(User.strava_id == str(athlete["id"])).first()
    if not user:
        user = User(
            name=athlete.get("firstname", "") + " " + athlete.get("lastname", ""),
            strava_id=str(athlete["id"]),
        )
        db.add(user)


    user.access_token = tokens["access_token"]
    user.refresh_token = tokens["refresh_token"]
    user.token_expires_at = datetime.datetime.fromtimestamp(tokens["expires_at"])


    db.commit()
    db.refresh(user)


    return {"message": f"User {user.name} authenticated successfully"}