"""Render's supplied database URL is used verbatim; no silent fallback."""
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

if os.getenv("LOAD_ENV_FILE", "0") == "1":
    from dotenv import load_dotenv
    load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    if os.getenv("RENDER") or os.getenv("REQUIRE_POSTGRES", "0") == "1":
        raise RuntimeError("DATABASE_URL must point to the existing PostgreSQL database")
    DATABASE_URL = "sqlite:///" + str(Path(__file__).with_name("dev.db"))
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if os.getenv("REQUIRE_POSTGRES", "0") == "1" and not DATABASE_URL.startswith("postgresql"):
    raise RuntimeError("REQUIRE_POSTGRES=1 requires PostgreSQL")
is_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(DATABASE_URL, pool_pre_ping=True,
                       connect_args={"check_same_thread": False} if is_sqlite else {"connect_timeout": 10})
if is_sqlite:
    @event.listens_for(engine, "connect")
    def sqlite_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
