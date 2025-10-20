# --- BACKEND STRUCTURE ---
# Path: backend/main.py


from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import logging
import traceback



# NEW: attempt to import heavy DB/mods/routers, but don't fail app startup on exceptions
DB_IMPORT_ERROR = None
DB_AVAILABLE = False
try:
	# try normal imports (may raise)
	from database import SessionLocal, engine, Base, get_db, ensure_slots_column, ensure_strava_id_column_type, DATABASE_URL, try_create_missing_database
	from models import user, activity, claim
	from auth.routes import router as auth_router
	from routes.activities import router as activities_router
	from routes.users import router as users_router
	from routes.strava_webhook import router as strava_webhook_router
	# perform DB migrations / init that may raise
	Base.metadata.create_all(bind=engine)
	ensure_slots_column(engine)
	ensure_strava_id_column_type(engine)
	DB_AVAILABLE = True
except Exception as e:
	DB_IMPORT_ERROR = traceback.format_exc()
	logging.exception("Database/Router import failed at startup: %s", e)
	# define minimal placeholders so code below can reference names if needed
	SessionLocal = None
	engine = None
	Base = None
	get_db = None
	DATABASE_URL = os.getenv("DATABASE_URL", "")
	# routers left undefined when DB not available

app = FastAPI(title="November Challenge API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers: only include full routers if DB and router imports succeeded
if DB_AVAILABLE:
	# full app behavior
	app.include_router(auth_router, prefix="/auth", tags=["auth"])
	app.include_router(strava_webhook_router, prefix="/auth", tags=["auth"])  # <- webhook handler
	app.include_router(users_router, prefix="/users", tags=["users"])
	app.include_router(activities_router, prefix="/activities", tags=["activities"])
else:
	# fallback: minimal info for debugging when DB/imports failed
	@app.get("/debug/nodb")
	def debug_nodb():
		# return the traceback (text) so you can copy/paste it — mask secrets in logs manually before sharing
		return {"db_import_error": DB_IMPORT_ERROR or "(no traceback captured)"}


@app.get("/")
def root():
    return {"message": "November Challenge API is running."}


@app.get("/debug/users_count")
def debug_users_count(db: Session = Depends(get_db)):
    from models.user import User
    count = db.query(User).count()
    return {"users_count": count}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/debug/db_info")
def debug_db_info(db: Session = Depends(get_db)):
	"""
	Return basic info about the database connection and some table counts / sample data.
	Use this to verify which DATABASE_URL is active on the running service.
	"""
	# mask password in netloc
	def _mask_netloc(netloc: str) -> str:
		if "@" in netloc and ":" in netloc.split("@")[0]:
			userinfo, hostinfo = netloc.split("@", 1)
			user = userinfo.split(":", 1)[0]
			return f"{user}:***@{hostinfo}"
		return netloc

	p = urlparse(DATABASE_URL or "")
	db_url_masked = f"{p.scheme}://{_mask_netloc(p.netloc)}{p.path}"

	# gather counts (safe queries)
	try:
		from models.user import User
		from models.activity import Activity
		from models.claim import Claim
		users_count = db.query(User).count()
		activities_count = db.query(Activity).count()
		claims_count = db.query(Claim).count()
		first_user = db.query(User).first()
		first_slots = None
		if first_user:
			# ensure slots is python data
			try:
				first_slots = first_user.slots
			except Exception:
				first_slots = str(first_user.slots)
	except Exception as e:
		# if models/tables missing, return error info
		return {"database_url": db_url_masked, "db_scheme": p.scheme, "error": str(e)}

	return {
		"database_url": db_url_masked,
		"db_scheme": p.scheme,
		"users_count": users_count,
		"activities_count": activities_count,
		"claims_count": claims_count,
		"first_user_slots_sample": first_slots
	}


@app.post("/admin/create_db")
def admin_create_db():
    """
    Admin helper: attempt to create the configured Postgres database using the DB server's 'postgres' maintenance DB.
    Returns JSON with success flag and message. Only for debugging / initial setup.
    """
    ok, msg = try_create_missing_database()
    return {"ok": ok, "message": msg}


@app.on_event("startup")
def _startup_log():
    # Log useful masked info at startup so you can check service logs in Render
    def _mask_netloc(netloc: str) -> str:
        if "@" in netloc and ":" in netloc.split("@")[0]:
            userinfo, hostinfo = netloc.split("@", 1)
            user = userinfo.split(":", 1)[0]
            return f"{user}:***@{hostinfo}"
        return netloc
    try:
        p = urlparse(DATABASE_URL or "")
        db_masked = f"{p.scheme}://{_mask_netloc(p.netloc)}{p.path}"
    except Exception:
        db_masked = "(invalid DATABASE_URL)"
    env_redirect = os.getenv("STRAVA_REDIRECT_URI", "")
    used_redirect = env_redirect if env_redirect.strip() and not env_redirect.strip().lower().startswith((
        "http://localhost", "https://localhost", "http://127.0.0.1", "https://127.0.0.1"
    )) else None
    logging.info("Startup config: STRAVA_REDIRECT_URI(env)=%s, used_redirect(base)=%s, DATABASE_URL=%s, DB_AVAILABLE=%s",
                 "(set)" if env_redirect else "(not set)", used_redirect or "(will use request base_url)", db_masked, DB_AVAILABLE)
    if not DB_AVAILABLE:
        logging.error("App started in fallback mode because DB/Router import failed. See /debug/nodb for traceback.")


# New global debug config endpoint (also available at /auth/debug/config)
@app.get("/debug/config")
@app.get("/auth/debug/config")
def debug_config(request: Request):
    def _mask_url(u: str) -> str:
        if not u:
            return "(not set)"
        try:
            if "@" in u and ":" in u.split("@")[0]:
                userinfo, hostinfo = u.split("@", 1)
                user = userinfo.split(":", 1)[0]
                return f"{user}:***@{hostinfo}"
        except Exception:
            pass
        return u if len(u) < 120 else u[:80] + "..."

    env_redirect = os.getenv("STRAVA_REDIRECT_URI", "")
    if env_redirect.strip() and not env_redirect.strip().lower().startswith((
        "http://localhost", "https://localhost", "http://127.0.0.1", "https://127.0.0.1"
    )):
        used_redirect = env_redirect
    else:
        used_redirect = str(request.base_url).rstrip("/") + "/auth/callback"

    return {
        "used_redirect_uri": used_redirect,
        "env_STRAVA_REDIRECT_URI_masked": _mask_url(env_redirect),
        "STRAVA_CLIENT_ID_set": bool(os.getenv("STRAVA_CLIENT_ID")),
        "DATABASE_URL_masked": _mask_url(os.getenv("DATABASE_URL", "")),
        "DB_AVAILABLE": DB_AVAILABLE,
        "notes": "If DB_AVAILABLE is false, check /debug/nodb and your Render service logs."
    }