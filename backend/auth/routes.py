"""OAuth code exchange. Strava credentials never enter browser storage or URLs."""
import hmac
import os
import secrets
import requests
from datetime import timedelta
from urllib.parse import urlencode, urlsplit
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from models.session import AuthSession, OAuthState
from models.user import User
from services.challenge import edition
from services.sessions import USER_COOKIE, digest, issue_session, cookie_options
from services.time import utcnow
from services.limits import limit

router = APIRouter()
STATE_COOKIE = "nc_oauth_state"

def frontend_url():
    return os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

def safe_return(value):
    parts = urlsplit(value)
    return value if value.startswith("/") and not value.startswith("//") and not parts.netloc and not parts.scheme and "\\" not in value and len(value) <= 400 else "/"

@router.get("/login")
def login(request: Request, return_to: str = "/", db: Session = Depends(get_db)):
    if not os.getenv("STRAVA_CLIENT_ID") or not os.getenv("STRAVA_CLIENT_SECRET"):
        raise HTTPException(503, "Strava ist noch nicht konfiguriert.")
    limit(db, request, "oauth", 30)
    state = secrets.token_urlsafe(32)
    db.query(OAuthState).filter(OAuthState.expires_at < utcnow()).delete(synchronize_session=False)
    db.add(OAuthState(token_hash=digest(state), return_to=safe_return(return_to), expires_at=utcnow() + timedelta(minutes=10)))
    db.commit()
    params = {"client_id": os.environ["STRAVA_CLIENT_ID"], "response_type": "code", "scope": "read,activity:read_all",
              "redirect_uri": os.getenv("STRAVA_REDIRECT_URI", str(request.base_url).rstrip("/") + "/auth/callback"),
              "approval_prompt": "auto", "state": state}
    response = RedirectResponse("https://www.strava.com/oauth/authorize?" + urlencode(params))
    response.set_cookie(STATE_COOKIE, state, max_age=600, **cookie_options(request))
    return response

@router.get("/callback")
def callback(request: Request, background_tasks: BackgroundTasks, code: str = "", state: str = "", error: str = "", scope: str = "", db: Session = Depends(get_db)):
    cookie = request.cookies.get(STATE_COOKIE, "")
    stored = db.get(OAuthState, digest(state)) if state else None
    if not cookie or not hmac.compare_digest(state, cookie) or not stored or stored.expires_at <= utcnow():
        raise HTTPException(400, "Die Anmeldung ist abgelaufen. Bitte erneut starten.")
    return_to = stored.return_to
    db.delete(stored)
    db.commit()
    missing_scope = bool(scope and "activity:read_all" not in scope.split(","))
    if error or not code or missing_scope:
        response = RedirectResponse(frontend_url() + "/?auth_error=" + ("scope" if missing_scope else "cancelled"), status_code=303)
        response.delete_cookie(STATE_COOKIE, **cookie_options(request))
        return response
    try:
        result = requests.post("https://www.strava.com/oauth/token", data={
            "client_id": os.environ["STRAVA_CLIENT_ID"], "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
            "code": code, "grant_type": "authorization_code"}, timeout=20)
        result.raise_for_status()
        data = result.json()
        athlete_id = int(data["athlete"]["id"])
        access, refresh, expiry = data["access_token"], data["refresh_token"], int(data["expires_at"])
    except (requests.RequestException, KeyError, ValueError, TypeError):
        response = RedirectResponse(frontend_url() + "/?auth_error=unavailable", status_code=303)
        response.delete_cookie(STATE_COOKIE, **cookie_options(request))
        return response
    edition(db, lock=True)  # serialize first logins for the same athlete
    user = db.query(User).filter_by(strava_id=athlete_id).first()
    name = " ".join(filter(None, [data["athlete"].get("firstname"), data["athlete"].get("lastname")]))[:100]
    if not user:
        user = User(strava_id=athlete_id, name=name or "Läufer/in")
        db.add(user)
        db.flush()
    user.access_token, user.refresh_token, user.token_expires_at = access, refresh, expiry
    # Keep an admin-corrected display name on subsequent logins.
    token = issue_session(db, user_id=user.id)
    db.commit()
    from services.strava import sync_user_background
    background_tasks.add_task(sync_user_background, user.id)
    response = RedirectResponse(frontend_url() + safe_return(return_to), status_code=303)
    response.set_cookie(USER_COOKIE, token, max_age=90 * 86400, **cookie_options(request))
    response.delete_cookie(STATE_COOKIE, **cookie_options(request))
    return response

@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(USER_COOKIE)
    if token:
        session = db.get(AuthSession, digest(token))
        if session and session.kind == "user":
            db.delete(session)
            db.commit()
    response = JSONResponse({"ok": True})
    response.delete_cookie(USER_COOKIE, **cookie_options(request))
    return response
