import asyncio
import logging
import os
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

if os.getenv("LOAD_ENV_FILE", "0") == "1":
    from dotenv import load_dotenv
    load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
DB_AVAILABLE = False

try:
    from database import engine, SessionLocal
    from migrations import migrate
    from services.challenge import seed
    migrate()
    with SessionLocal() as db:
        seed(db)
    from auth.routes import router as auth_router
    from routes.users import router as users_router
    from routes.challenge import router as challenge_router
    from routes.community import router as community_router
    from routes.admin import router as admin_router
    from routes.strava_webhook import router as webhook_router
    DB_AVAILABLE = True
except Exception as exc:
    # Log exception type only: connection errors can contain database passwords.
    log.error("API initialization failed (%s). Check DATABASE_URL and schema permissions.", type(exc).__name__)

@asynccontextmanager
async def lifespan(app):
    task = None
    if DB_AVAILABLE and os.getenv("ENABLE_BACKGROUND_SYNC", "1") == "1":
        from tasks.sync_scheduler import background_sync_loop
        task = asyncio.create_task(background_sync_loop())
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

app = FastAPI(title="November Challenge API", version="2026.1", lifespan=lifespan)
origins = {"http://localhost:5173", "http://127.0.0.1:5173"} if not os.getenv("RENDER") else set()
for env in ("FRONTEND_URL", "CUSTOM_DOMAIN", "ALLOWED_ORIGINS"):
    origins.update(value.strip().rstrip("/") for value in os.getenv(env, "").split(",") if value.strip())
app.add_middleware(CORSMiddleware, allow_origins=sorted(origins), allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                   allow_headers=["Content-Type", "X-Admin-Token"])

@app.middleware("http")
async def guard(request: Request, call_next):
    if not DB_AVAILABLE and request.url.path not in {"/", "/healthz"}:
        return JSONResponse({"detail": "Backend derzeit nicht verfügbar. Bitte später erneut versuchen."}, 503)
    if request.method in {"POST", "PUT", "DELETE", "PATCH"} and request.url.path != "/auth/webhook":
        origin = request.headers.get("origin")
        own = f"{request.url.scheme}://{request.url.netloc}"
        if origin and origin not in origins and origin != own:
            return JSONResponse({"detail": "Diese Herkunft ist nicht zugelassen."}, 403)
    response = await call_next(request)
    if request.url.path.startswith(("/auth", "/users/me", "/admin", "/community")):
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

if DB_AVAILABLE:
    for prefix, router, tag in (("/auth", auth_router, "auth"), ("/auth", webhook_router, "strava"),
        ("/users", users_router, "users"), ("/challenge", challenge_router, "challenge"),
        ("/community", community_router, "community"), ("/admin", admin_router, "admin")):
        app.include_router(router, prefix=prefix, tags=[tag])
    if os.getenv("ENABLE_DEBUG_ROUTES", "0") == "1":
        from routes.diagnostics import router
        app.include_router(router, tags=["diagnostics"])

@app.get("/")
def root():
    return {"message": "November Challenge API", "version": "2026.1"}

@app.get("/healthz")
def healthz():
    available = DB_AVAILABLE
    if available:
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            available = False
    return JSONResponse({"status": "ok" if available else "unavailable", "database_available": available}, 200 if available else 503)
