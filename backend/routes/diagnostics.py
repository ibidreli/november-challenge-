"""Optional maintenance routes. Enable with ENABLE_DEBUG_ROUTES=1."""

import os

from fastapi import APIRouter, Depends, Request
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from database import DATABASE_URL, get_db
from models.user import User
from models.activity import Activity
from models.claim import Claim
from routes.admin import verify_admin_token

router = APIRouter(dependencies=[Depends(verify_admin_token)])


@router.get("/debug/users_count")
def users_count(db: Session = Depends(get_db)):
    return {"users_count": db.query(User).count()}


@router.get("/debug/db_info")
def db_info(db: Session = Depends(get_db)):
    url = make_url(DATABASE_URL)
    return {
        "database_url": url.render_as_string(hide_password=True),
        "db_scheme": url.drivername,
        "users_count": db.query(User).count(),
        "activities_count": db.query(Activity).count(),
        "claims_count": db.query(Claim).count(),
    }


@router.get("/debug/config")
@router.get("/auth/debug/config", include_in_schema=False)
def config(request: Request):
    return {
        "used_redirect_uri": os.getenv("STRAVA_REDIRECT_URI") or
            str(request.base_url).rstrip("/") + "/auth/callback",
        "STRAVA_CLIENT_ID_set": bool(os.getenv("STRAVA_CLIENT_ID")),
        "backend_base_url": str(request.base_url).rstrip("/"),
        "DB_AVAILABLE": True,
    }

