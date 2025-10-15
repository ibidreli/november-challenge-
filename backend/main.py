# --- BACKEND STRUCTURE ---
# Path: backend/main.py


from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base, get_db, ensure_slots_column, ensure_strava_id_column_type, DATABASE_URL, try_create_missing_database
from models import user, activity, claim
from auth.routes import router as auth_router
from routes.activities import router as activities_router
from routes.users import router as users_router
from routes.strava_webhook import router as strava_webhook_router
from urllib.parse import urlparse



Base.metadata.create_all(bind=engine)

# ensure legacy DB that lacked 'slots' gets the column added
ensure_slots_column(engine)

# ensure strava_id column has integer type in Postgres (auto-convert if safe)
ensure_strava_id_column_type(engine)

app = FastAPI(title="November Challenge API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(strava_webhook_router, prefix="/auth", tags=["auth"])  # <- webhook handler
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(activities_router, prefix="/activities", tags=["activities"])


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