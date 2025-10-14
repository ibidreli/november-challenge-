# --- BACKEND STRUCTURE ---
# Path: backend/main.py


from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base, get_db, ensure_slots_column, ensure_strava_id_column_type
from models import user, activity, claim
from auth.routes import router as auth_router
from routes.activities import router as activities_router
from routes.users import router as users_router
from routes.strava_webhook import router as strava_webhook_router



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