from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
import logging
import traceback
from fastapi.responses import JSONResponse, HTMLResponse
from urllib.parse import urlparse
import asyncio
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- BACKEND STRUCTURE ---
# Path: backend/main.py


FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip()
CUSTOM_DOMAIN = os.getenv("CUSTOM_DOMAIN", "").strip()
DEFAULT_FRONTEND = "https://november-challenge-1.onrender.com"

# NEW: Define lifespan BEFORE FastAPI() initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/Shutdown logic für Background-Tasks."""
    # STARTUP
    logger.info("Starting background sync task...")
    try:
        from tasks.sync_scheduler import background_sync_loop
        sync_task = asyncio.create_task(background_sync_loop())
    except Exception as e:
        logger.error("Failed to start background sync task: %s", e)
        sync_task = None
    
    yield
    
    # SHUTDOWN
    if sync_task:
        logger.info("Stopping background sync task...")
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            logger.info("Background sync task stopped")

# NEW: attempt to import heavy DB/mods/routers, but don't fail app startup on exceptions
DB_IMPORT_ERROR = None
DB_AVAILABLE = False
try:
	# try normal imports (may raise)
	from database import SessionLocal, engine, Base, get_db, ensure_slots_column, ensure_strava_id_column_type, ensure_is_manual_column, DATABASE_URL, try_create_missing_database
	from models import user, activity, claim
	from auth.routes import router as auth_router
	from routes.activities import router as activities_router
	from routes.users import router as users_router
	from routes.strava_webhook import router as strava_webhook_router
	from routes.admin import router as admin_router
	# perform DB migrations / init that may raise
	Base.metadata.create_all(bind=engine)
	ensure_slots_column(engine)
	ensure_strava_id_column_type(engine)
	ensure_is_manual_column(engine)
	DB_AVAILABLE = True
except Exception as e:
	DB_IMPORT_ERROR = traceback.format_exc()
	logging.exception("Database/Router import failed at startup: %s", e)
	# define minimal placeholders so code below can reference names if needed
	SessionLocal = None
	engine = None
	Base = None
	# provide a fallback dependency function so FastAPI's dependency analysis does not fail.
	# When called at runtime this will return a clear 503 response.
	from fastapi import HTTPException
	def get_db():
		# raising HTTPException here ensures endpoints using Depends(get_db) return 503
		# instead of causing import/analysis errors at startup.
		raise HTTPException(status_code=503, detail="Database not available (see /debug/nodb for details)")
	DATABASE_URL = os.getenv("DATABASE_URL", "")
	# routers left undefined when DB not available

# NOW create app with lifespan
app = FastAPI(title="November Challenge API", lifespan=lifespan)

# Build list of allowed origins
allow_origins = []

# Add custom domain if provided (priority)
if CUSTOM_DOMAIN:
    allow_origins.append(CUSTOM_DOMAIN)

# Add FRONTEND_URL if explicitly set
if FRONTEND_URL:
    allow_origins.append(FRONTEND_URL)

# Always add default Render frontend as fallback
if DEFAULT_FRONTEND not in allow_origins:
    allow_origins.append(DEFAULT_FRONTEND)

# Log allowed origins for debugging
logging.info(f"CORS allowed origins: {allow_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
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
	app.include_router(admin_router, prefix="/admin", tags=["admin"])  # NEW: Admin management


else:
	# fallback: minimal info for debugging when DB/imports failed
	@app.get("/debug/nodb")
	def debug_nodb():
		# return the traceback (text) so you can copy/paste it — mask secrets in logs manually before sharing
		return {"db_import_error": DB_IMPORT_ERROR or "(no traceback captured)"}

	# --- NEW: friendly fallback endpoints so frontend calls don't get 404 ---

	@app.get("/users/me")
	def fallback_users_me():
		# Called by frontend; return 503 with clear instructions instead of 404.
		return JSONResponse(
			status_code=503,
			content={
				"error": "service_unavailable",
				"reason": "DB or router import failed on startup",
				"hint": "Check /debug/nodb and service logs in Render for the full traceback"
			}
		)

	@app.get("/activities")
	def fallback_activities():
		return JSONResponse(
			status_code=503,
			content={
				"error": "service_unavailable",
				"reason": "Activities router unavailable because DB/import failed",
				"hint": "Check /debug/nodb and Render logs"
			}
		)

	@app.get("/auth/login")
	def fallback_auth_login():
		# Provide an informative HTML page for browser attempts to login
		# show masked traceback if available to speed up debugging (do not leak secrets)
		trace = DB_IMPORT_ERROR or "(no traceback captured)"
		# keep it short: show first ~2000 chars
		trace_short = trace if len(trace) <= 2000 else trace[:2000] + "\n\n...(truncated)"
		# HTML with guidance
		html = (
			"<!doctype html><html><head><meta charset='utf-8'><title>Service nicht verfügbar</title></head>"
			"<body style='font-family:Arial,sans-serif;padding:20px'>"
			"<h2>Service vorübergehend nicht verfügbar</h2>"
			"<p>Der Auth‑Login ist aktuell nicht verfügbar, weil beim Start der Anwendung ein Fehler aufgetreten ist.</p>"
			"<h3>Diagnose (kurze Traceback‑Vorschau)</h3>"
			"<pre style='background:#f6f6f6;padding:10px;border-radius:4px;white-space:pre-wrap;max-height:420px;overflow:auto;'>"
			+ trace_short.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") +
			"</pre>"
			"<p>Weitere Schritte:</p>"
			"<ol>"
			"<li>Rufe <a href='/debug/nodb'>/debug/nodb</a> auf, um den vollständigen Traceback zu sehen.</li>"
			"<li>Prüfe, ob die Datei <code>auth/routes.py</code> syntaktisch korrekt ist (keine f-string/JS‑Braces Konflikte).</li>"
			"<li>Stelle sicher, dass Umgebungsvariablen korrekt sind:<br>"
			"<code>DATABASE_URL</code> (Postgres) und <code>FRONTEND_URL</code> (z. B. https://november-challenge-1.onrender.com).</li>"
			"<li>Bei Fragen: kopiere den Traceback (aus /debug/nodb) und sende ihn hier.</li>"
			"</ol>"
			"</body></html>"
		)
		return HTMLResponse(content=html, status_code=503)

	@app.get("/auth/callback")
	def fallback_auth_callback():
		# Provide a helpful HTML page when the OAuth callback route is unavailable due to startup error.
		trace = DB_IMPORT_ERROR or "(no traceback captured)"
		trace_short = trace if len(trace) <= 2000 else trace[:2000] + "\n\n...(truncated)"
		html = (
			"<!doctype html><html><head><meta charset='utf-8'><title>Auth Callback unavailable</title></head>"
			"<body style='font-family:Arial,sans-serif;padding:20px'>"
			"<h2>Auth Callback nicht verfügbar</h2>"
			"<pre style='background:#f6f6f6;padding:10px;border-radius:4px;white-space:pre-wrap;max-height:420px;overflow:auto;'>"
			+ trace_short.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") +
			"</pre>"
			"</body></html>"
		)
		return HTMLResponse(content=html, status_code=503)

	@app.get("/auth/token")
	def fallback_auth_token():
		# Fallback for token exchange endpoint (when auth router not loaded)
		return JSONResponse(
			status_code=503,
			content={
				"error": "service_unavailable",
				"reason": "auth token endpoint unavailable because server failed to register auth router at startup",
				"hint": "Check /debug/nodb and Render logs for the startup traceback"
			}
		)

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
         # actual backend base URL as seen by the running process (use this as API base in frontend)
         "backend_base_url": str(request.base_url).rstrip("/"),
         "DB_AVAILABLE": DB_AVAILABLE,
         "notes": "If DB_AVAILABLE is false, check /debug/nodb and your Render service logs."
     }