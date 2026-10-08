"""Additive, transactional migration. Historical users/results remain intact."""
from sqlalchemy import inspect, text
from database import Base, engine
import models

REVISION = "2026_02_weekly"
MONTH_REVISION = "2026_04_challenge_month"


def migrate_month(conn):
    columns = {c["name"] for c in inspect(conn).get_columns("challenge_editions")}
    if "month" not in columns:
        conn.execute(text("ALTER TABLE challenge_editions ADD COLUMN month INTEGER NOT NULL DEFAULT 11"))
    if "finale_on" not in columns:
        conn.execute(text("ALTER TABLE challenge_editions ADD COLUMN finale_on DATE"))
    # Preserve an already-created October edition from the previous implementation.
    if "is_test" in columns:
        conn.execute(text("UPDATE challenge_editions SET month=10 WHERE is_test=TRUE"))
    unique = inspect(conn).get_unique_constraints("challenge_editions")
    if conn.dialect.name == "sqlite" and any(c["column_names"] == ["year"] for c in unique):
        # SQLite cannot drop an inline UNIQUE constraint. Rebuild only this parent
        # table, preserving IDs so all periods, targets and claims keep their links.
        conn.execute(text("""CREATE TABLE challenge_editions_month_upgrade (
            id INTEGER NOT NULL PRIMARY KEY, year INTEGER NOT NULL,
            month INTEGER NOT NULL DEFAULT 11, timezone VARCHAR(50) NOT NULL,
            finale_km INTEGER NOT NULL, finale_on DATE,
            CONSTRAINT uq_challenge_editions_year_month UNIQUE (year, month))"""))
        conn.execute(text("""INSERT INTO challenge_editions_month_upgrade
            (id,year,month,timezone,finale_km,finale_on)
            SELECT id,year,month,COALESCE(timezone,'Europe/Zurich'),COALESCE(finale_km,15),finale_on
            FROM challenge_editions"""))
        conn.execute(text("DROP TABLE challenge_editions"))
        conn.execute(text("ALTER TABLE challenge_editions_month_upgrade RENAME TO challenge_editions"))
        if conn.exec_driver_sql("PRAGMA foreign_key_check").first():
            raise RuntimeError("Challenge month migration found an invalid foreign key")
    elif conn.dialect.name == "postgresql":
        quote = conn.dialect.identifier_preparer.quote
        for constraint in unique:
            if constraint["column_names"] == ["year"]:
                conn.execute(text(f"ALTER TABLE challenge_editions DROP CONSTRAINT {quote(constraint['name'])}"))
        if not any(c["column_names"] == ["year", "month"] for c in unique):
            conn.execute(text("ALTER TABLE challenge_editions ADD CONSTRAINT uq_challenge_editions_year_month UNIQUE (year, month)"))


def migrate():
    with engine.connect() as conn:
        sqlite = conn.dialect.name == "sqlite"
        if sqlite:
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
            conn.commit()
        try:
            with conn.begin():
                if sqlite:
                    conn.exec_driver_sql("BEGIN")
                elif conn.dialect.name == "postgresql":
                    conn.execute(text("SELECT pg_advisory_xact_lock(2026100701)"))
                conn.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (revision VARCHAR(80) PRIMARY KEY)"))
                weekly_applied = conn.execute(text("SELECT revision FROM schema_migrations WHERE revision=:r"), {"r": REVISION}).first()
                month_applied = conn.execute(text("SELECT revision FROM schema_migrations WHERE revision=:r"), {"r": MONTH_REVISION}).first()
                if weekly_applied and month_applied:
                    return
                Base.metadata.create_all(conn)
                if not weekly_applied:
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
                if not month_applied:
                    migrate_month(conn)
                    conn.execute(text("INSERT INTO schema_migrations (revision) VALUES (:r)"), {"r": MONTH_REVISION})
        finally:
            if sqlite:
                conn.exec_driver_sql("PRAGMA foreign_keys=ON")
                conn.commit()
