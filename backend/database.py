from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os
import logging
from urllib.parse import urlparse
from sqlalchemy import text

# load variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# If no DATABASE_URL provided, use sqlite fallback for local dev
if not DATABASE_URL:
    logging.warning("DATABASE_URL not set — falling back to local sqlite database (./dev.db).")
    DATABASE_URL = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'dev.db')}"

# detect obvious placeholders like <DB_PORT> or any <...> tokens
def _contains_placeholders(s: str) -> bool:
    return "<" in s or ">" in s or s.strip() == "" or s.strip().startswith("<") 

# detect non-numeric port without triggering urlparse.port ValueError
def _port_invalid(s: str) -> bool:
    try:
        p = urlparse(s)
        netloc = p.netloc or ""
        # remove userinfo if present
        if "@" in netloc:
            hostinfo = netloc.split("@", 1)[1]
        else:
            hostinfo = netloc
        if ":" in hostinfo:
            port = hostinfo.rsplit(":", 1)[1]
            # common placeholders like <DB_PORT> contain non-digits
            return not port.isdigit()
        return False
    except Exception:
        return True

# If placeholders or invalid port detected, log and switch to sqlite fallback
if _contains_placeholders(DATABASE_URL) or _port_invalid(DATABASE_URL):
    logging.warning(
        "DATABASE_URL appears to contain placeholders or an invalid port. "
        "Using local sqlite fallback (./dev.db). "
        "Set a valid DATABASE_URL in your .env to connect to Postgres."
    )
    DATABASE_URL = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'dev.db')}"

# Only append client_encoding for non-sqlite URLs
if not DATABASE_URL.startswith("sqlite"):
    if "?" in DATABASE_URL and not DATABASE_URL.endswith("&"):
        DATABASE_URL += "&client_encoding=utf8"
    elif "?" not in DATABASE_URL:
        DATABASE_URL += "?client_encoding=utf8"

# enable basic logging for debugging DB connection (mask password)
logging.basicConfig(level=logging.INFO)
p = urlparse(DATABASE_URL)
def _mask_netloc(netloc: str) -> str:
    # mask password in user:pass@host form
    if "@" in netloc and ":" in netloc.split("@")[0]:
        userinfo, hostinfo = netloc.split("@", 1)
        user = userinfo.split(":", 1)[0]
        return f"{user}:***@{hostinfo}"
    return netloc

logging.info(f"Connecting to DB: {p.scheme}://{_mask_netloc(p.netloc)}{p.path}")

# Create engine and verify connection; on failure fall back to sqlite
try:
    engine = create_engine(DATABASE_URL, echo=True, future=True)
    # verify connection quickly (some drivers attempt lazy connect)
    try:
        with engine.connect() as conn:
            pass
    except Exception as conn_err:
        logging.exception("Initial DB connection test failed: %s", conn_err)
        raise
except Exception:
    # fallback to sqlite local file
    logging.warning("Falling back to local sqlite database (./dev.db) due to connection error.")
    DATABASE_URL = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'dev.db')}"
    logging.info(f"Connecting to DB: sqlite:///{os.path.join(os.path.dirname(__file__), 'dev.db')}")
    engine = create_engine(DATABASE_URL, echo=True, future=True)

# new helper: ensure 'slots' column exists and initialize it (Postgres only)
def ensure_slots_column(engine):
    """
    For Postgres: add JSON 'slots' column to users table if missing and initialize
    existing rows with a 30-entry JSON array of nulls.
    No-op for non-postgres URLs.
    """
    try:
        p = urlparse(DATABASE_URL or "")
        if not p.scheme or not p.scheme.startswith("postgres"):
            # only handle Postgres automatic migration here
            return
        nulls = ",".join(["null"] * 30)
        with engine.begin() as conn:
            # check existence
            res = conn.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'slots'
                LIMIT 1
            """))
            if res.first():
                return
            logging.info("Adding 'slots' column to users table (automatic startup migration).")
            # add column (allow NULL temporarily), initialize rows, then set NOT NULL and default
            conn.execute(text("ALTER TABLE users ADD COLUMN slots JSON"))
            conn.execute(text(f"UPDATE users SET slots = '[{nulls}]'::json WHERE slots IS NULL"))
            conn.execute(text("ALTER TABLE users ALTER COLUMN slots SET DEFAULT '[]'::json"))
            conn.execute(text("ALTER TABLE users ALTER COLUMN slots SET NOT NULL"))
            logging.info("'slots' column added and initialized.")
    except Exception:
        logging.exception("Failed to ensure 'slots' column exists. Manual migration may be required.")

# new helper: ensure 'strava_id' column is integer type in Postgres
def ensure_strava_id_column_type(engine):
    """
    For Postgres: if users.strava_id is character varying/text, and all values are numeric,
    convert the column to bigint using ALTER TABLE ... USING strava_id::bigint.
    If non-numeric values exist, log a warning and do nothing (manual migration required).
    No-op for non-postgres DBs.
    """
    try:
        p = urlparse(DATABASE_URL or "")
        if not p.scheme or not p.scheme.startswith("postgres"):
            return
        with engine.begin() as conn:
            col = conn.execute(text("""
                SELECT data_type FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'strava_id'
                LIMIT 1
            """)).first()
            if not col:
                # no column present yet (models may create it later)
                return
            data_type = col[0]
            if data_type in ("integer", "bigint", "numeric"):
                return
            if data_type not in ("character varying", "text"):
                # unexpected type, log and skip
                logging.warning("users.strava_id has unexpected SQL type '%s'; manual migration may be needed.", data_type)
                return
            # check for non-numeric values
            non_numeric = conn.execute(text("SELECT COUNT(*) FROM users WHERE strava_id !~ '^[0-9]+$'")).scalar()
            if non_numeric and int(non_numeric) > 0:
                logging.warning("Found %s non-numeric users.strava_id values — cannot auto-convert. Clean data or run manual migration.", non_numeric)
                return
            logging.info("Converting users.strava_id from %s to bigint (automatic startup migration).", data_type)
            conn.execute(text("ALTER TABLE users ALTER COLUMN strava_id TYPE bigint USING strava_id::bigint"))
            logging.info("Conversion of users.strava_id to bigint completed.")
    except Exception:
        logging.exception("Failed to ensure/convert 'strava_id' column type. Manual migration may be required.")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()