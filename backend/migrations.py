"""Additive, transactional migration. Historical users/results remain intact."""
from sqlalchemy import inspect, text
from database import Base, engine
import models

REVISION = "2026_02_weekly"
def migrate():
    with engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(2026100701)"))
        conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (revision VARCHAR(80) PRIMARY KEY)"))
        if conn.execute(text("SELECT revision FROM schema_migrations WHERE revision=:r"), {"r": REVISION}).first():
            return
        Base.metadata.create_all(conn)
        additions = {"users": {"slots": "JSON", "token_expires_at": "BIGINT", "last_synced_at": "TIMESTAMP", "last_sync_attempt_at": "TIMESTAMP", "last_sync_error": "VARCHAR(120)"},
                     "activities": {"is_manual": "BOOLEAN DEFAULT FALSE", "started_at": "TIMESTAMP"}}
        for table, columns in additions.items():
            existing = {c["name"] for c in inspect(conn).get_columns(table)}
            for name, sql_type in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))
        conn.execute(text("UPDATE users SET slots='[null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null]' WHERE slots IS NULL"))
        if conn.dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE users ALTER COLUMN strava_id TYPE BIGINT USING NULLIF(strava_id::text, '')::bigint"))
        conn.execute(text("INSERT INTO schema_migrations (revision) VALUES (:r)"), {"r": REVISION})
