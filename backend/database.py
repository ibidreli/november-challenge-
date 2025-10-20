from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import logging
from urllib.parse import urlparse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# load variables: load .env only when explicitly requested (avoid using repo .env in production)
from dotenv import load_dotenv
if os.getenv("LOAD_ENV_FILE", "0") == "1":
    # developer opt-in to load .env (useful for local dev)
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# If no DATABASE_URL provided, use sqlite fallback for local dev
if not DATABASE_URL:
    logging.warning("DATABASE_URL not set — falling back to local sqlite database (./dev.db).")
    DATABASE_URL = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'dev.db')}"

# Warn if DATABASE_URL points to localhost (common deploy mistake)
if isinstance(DATABASE_URL, str) and ("localhost" in DATABASE_URL or "127.0.0.1" in DATABASE_URL):
    logging.warning(
        "Detected DATABASE_URL pointing to localhost/127.0.0.1. "
        "When deploying to Render (oder einen anderen Host), set DATABASE_URL to the managed Postgres URL provided by the platform. "
        "A localhost DB is not reachable from the cloud service and will cause connection failures."
    )

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

# NEW: optional safety check to avoid running with sqlite in production.
# Set env REQUIRE_POSTGRES=1 in Render service to enforce using Postgres (will raise on startup if still sqlite).
if os.getenv("REQUIRE_POSTGRES", "0") == "1" and DATABASE_URL and DATABASE_URL.startswith("sqlite"):
    logging.error("REQUIRE_POSTGRES is set but DATABASE_URL points to sqlite. Set a Postgres DATABASE_URL in Render env.")
    raise RuntimeError("REQUIRE_POSTGRES=1 requires a Postgres DATABASE_URL. Set DATABASE_URL in Render to a Postgres URL and redeploy.")

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

def _build_admin_url_for_db(url):
	"""
	Build a connection URL that points to the 'postgres' maintenance DB on the same host,
	so we can attempt to CREATE DATABASE <target>.
	"""
	try:
		from sqlalchemy.engine import url as sa_url
		u = sa_url.make_url(url)
		driver = u.drivername
		user = u.username or ""
		password = u.password or ""
		host = u.host or "localhost"
		port = u.port or None
		# construct auth part
		auth = ""
		if user:
			auth = user
			if password:
				auth += ":" + password
			auth += "@"
		port_part = f":{port}" if port else ""
		admin_url = f"{driver}://{auth}{host}{port_part}/postgres"
		return admin_url, u.database
	except Exception:
		return None, None

def _try_create_database(url):
	"""
	If possible, connect to the server's 'postgres' DB and issue CREATE DATABASE <name>.
	Return True if database created (or already exists), False otherwise.
	"""
	try:
		admin_url, target_db = _build_admin_url_for_db(url)
		if not admin_url or not target_db:
			logging.info("Unable to derive admin URL for database creation.")
			return False
		logging.info("Attempting to create database '%s' via admin URL.", target_db)
		# connect to admin db and attempt to create target database
		admin_engine = create_engine(admin_url, future=True)
		with admin_engine.connect() as conn:
			# check if DB already exists (this can run inside a transaction)
			res = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :d"), {"d": target_db})
			if res.first():
				logging.info("Database '%s' already exists.", target_db)
				return True
			# CREATE DATABASE must run outside a transaction -> use autocommit
			try:
				conn_autocommit = conn.execution_options(isolation_level="AUTOCOMMIT")
				conn_autocommit.execute(text(f'CREATE DATABASE "{target_db}"'))
				logging.info("Database '%s' created successfully.", target_db)
				return True
			except OperationalError as e:
				logging.exception("CREATE DATABASE failed: %s", e)
				return False
			except Exception:
				# some providers disallow CREATE DATABASE, will fail here
				logging.exception("CREATE DATABASE attempt failed (likely not permitted by provider).")
				return False
	except Exception:
		logging.exception("Failed to attempt creating database via admin connection.")
		return False

# NEW: allow sqlite fallback only when explicitly enabled (default: disabled)
# Allow sqlite fallback by default here so the service can start while you fix Postgres.
# In production set ALLOW_SQLITE_FALLBACK=0 and ensure DATABASE_URL points to a working Postgres.
ALLOW_SQLITE_FALLBACK = os.getenv("ALLOW_SQLITE_FALLBACK", "1") == "1"

def try_create_missing_database():
    """
    Public wrapper: attempt to create the target database on the server (if Postgres).
    Returns (True, message) on success or (False, message) on failure.
    """
    try:
        if not DATABASE_URL or not DATABASE_URL.startswith("postgres"):
            return False, "Not a Postgres DATABASE_URL"
        created = _try_create_database(DATABASE_URL)
        if created:
            return True, "Database created or already exists"
        return False, "CREATE DATABASE attempt failed (see logs)"
    except Exception as e:
        logging.exception("try_create_missing_database failed: %s", e)
        return False, f"Exception: {e}"

# Create engine and verify connection; on failure try to create DB (if postgres) then fall back to sqlite only if allowed
try:
    engine = create_engine(DATABASE_URL, echo=True, future=True)
    # verify connection quickly (some drivers attempt lazy connect)
    try:
        with engine.connect() as conn:
            pass
    except Exception as conn_err:
        logging.exception("Initial DB connection test failed: %s", conn_err)
        # if postgres and error indicates DB missing, try to create it and retry
        if DATABASE_URL and DATABASE_URL.startswith("postgres"):
            created = _try_create_database(DATABASE_URL)
            if created:
                # retry engine
                try:
                    engine = create_engine(DATABASE_URL, echo=True, future=True)
                    with engine.connect() as conn2:
                        pass
                except Exception as e:
                    logging.exception("Retry after CREATE DATABASE failed: %s", e)
                    # If fallback allowed, fall back; otherwise raise
                    if ALLOW_SQLITE_FALLBACK:
                        raise
                    else:
                        raise RuntimeError(f"Failed to connect to Postgres after CREATE DB attempt: {e}") from e
            else:
                # couldn't create DB
                msg = "Could not create target database on Postgres server. Please create it in your DB provider or check credentials."
                logging.error(msg)
                if ALLOW_SQLITE_FALLBACK:
                    raise
                else:
                    raise RuntimeError(msg)
        else:
            # non‑Postgres or other error: follow fallback only if allowed
            logging.exception("DB connection failed and not postgres/creation not attempted: %s", conn_err)
            if ALLOW_SQLITE_FALLBACK:
                raise
            else:
                raise RuntimeError(f"Database connection failed: {conn_err}") from conn_err
except Exception as e:
    # if allowed, fallback; otherwise re-raise to surface the error in logs (and make service fail)
    if ALLOW_SQLITE_FALLBACK:
        logging.warning("Falling back to local sqlite database (./dev.db) due to connection error: %s", e)
        DATABASE_URL = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'dev.db')}"
        logging.info(f"Connecting to DB: sqlite:///{os.path.join(os.path.dirname(__file__), 'dev.db')}")
        engine = create_engine(DATABASE_URL, echo=True, future=True)
    else:
        logging.critical("Database initialization failed and ALLOW_SQLITE_FALLBACK!=1. Aborting startup. Error: %s", e)
        raise

# new helper: ensure 'slots' column exists and initialize it (Postgres and SQLite)
def ensure_slots_column(engine):
    """
    Ensure 'slots' column exists on users table.
    - Postgres: add JSON column, initialize rows and set NOT NULL/default.
    - SQLite: ALTER TABLE ADD COLUMN (TEXT) and initialize rows with JSON array string.
    No-op for other DBs.
    """
    try:
        p = urlparse(DATABASE_URL or "")
        nulls = ",".join(["null"] * 30)
        json_value = f"[{nulls}]"
        with engine.begin() as conn:
            # Postgres path (unchanged behavior)
            if p.scheme and p.scheme.startswith("postgres"):
                res = conn.execute(text("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'users' AND column_name = 'slots'
                    LIMIT 1
                """))
                if res.first():
                    return
                logging.info("Adding 'slots' column to users table (automatic startup migration).")
                conn.execute(text("ALTER TABLE users ADD COLUMN slots JSON"))
                conn.execute(text(f"UPDATE users SET slots = '[{nulls}]'::json WHERE slots IS NULL"))
                conn.execute(text("ALTER TABLE users ALTER COLUMN slots SET DEFAULT '[]'::json"))
                conn.execute(text("ALTER TABLE users ALTER COLUMN slots SET NOT NULL"))
                logging.info("'slots' column added and initialized (Postgres).")
                return

            # SQLite path
            if p.scheme and p.scheme.startswith("sqlite"):
                # check users table exists
                t = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")).fetchone()
                if not t:
                    return
                # check existing columns
                cols = [row[1] for row in conn.execute(text("PRAGMA table_info('users')")).fetchall()]
                if "slots" in cols:
                    return
                logging.info("Adding 'slots' column to users table (SQLite automatic startup migration).")
                # add column as TEXT (store JSON string)
                conn.execute(text("ALTER TABLE users ADD COLUMN slots TEXT"))
                # initialize existing rows where NULL or empty
                conn.execute(text("UPDATE users SET slots = :val WHERE slots IS NULL OR slots = ''"), {"val": json_value})
                logging.info("'slots' column added and initialized (SQLite).")
                return

            # other DBs: no-op
            return
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