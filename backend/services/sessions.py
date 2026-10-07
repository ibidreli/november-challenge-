import hashlib
import os
import secrets
from datetime import timedelta
from fastapi import Depends, HTTPException, Request, Response, Header
from sqlalchemy.orm import Session
from database import get_db
from models.session import AuthSession
from models.user import User
from services.time import utcnow

USER_COOKIE = "nc_session"
GUEST_COOKIE = "nc_guest"
SESSION_DAYS = 90

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def cookie_options(request):
    secure = os.getenv("COOKIE_SECURE", "1" if os.getenv("RENDER") else "0") == "1"
    return {"httponly": True, "secure": secure, "samesite": "lax", "path": "/"}

def issue_session(db, kind="user", user_id=None, days=SESSION_DAYS):
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=digest(token), kind=kind, user_id=user_id,
                       expires_at=utcnow() + timedelta(days=days)))
    db.query(AuthSession).filter(AuthSession.expires_at < utcnow()).delete(synchronize_session=False)
    return token

def optional_user(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(USER_COOKIE)
    if not token:
        return None
    session = db.get(AuthSession, digest(token))
    if not session or session.kind != "user" or session.expires_at <= utcnow():
        response.delete_cookie(USER_COOKIE, **cookie_options(request))
        return None
    user = db.get(User, session.user_id)
    if user and session.expires_at < utcnow() + timedelta(days=30):
        session.expires_at = utcnow() + timedelta(days=SESSION_DAYS)
        db.commit()
        response.set_cookie(USER_COOKIE, token, max_age=SESSION_DAYS * 86400, **cookie_options(request))
    return user

def require_user(user=Depends(optional_user)):
    if not user:
        raise HTTPException(401, "Bitte mit Strava anmelden.")
    return user

def verify_admin_token(x_admin_token: str = Header(default=""), db: Session = Depends(get_db)):
    session = db.get(AuthSession, digest(x_admin_token)) if x_admin_token else None
    if not session or session.kind != "admin" or session.expires_at <= utcnow():
        raise HTTPException(401, "Admin-Anmeldung fehlt oder ist abgelaufen.")
    return session

def guest_identity(request, response):
    token = request.cookies.get(GUEST_COOKIE, "")
    if not token or len(token) < 32 or len(token) > 100:
        token = secrets.token_urlsafe(32)
        response.set_cookie(GUEST_COOKIE, token, max_age=SESSION_DAYS * 86400, **cookie_options(request))
    return digest(token)
