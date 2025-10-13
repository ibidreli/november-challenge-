# --- BACKEND STRUCTURE ---
# Path: backend/main.py


from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import user, activity
from auth.routes import router as auth_router
from routes.activities import router as activities_router
from routes.users import router as users_router



Base.metadata.create_all(bind=engine)


app = FastAPI(title="November Challenge API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency for DB sessions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(activities_router, prefix="/activities", tags=["activities"])


@app.get("/")
def root():
    return {"message": "November Challenge API is running."}