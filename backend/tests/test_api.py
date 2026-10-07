"""Isolated SQLite or PostgreSQL tests. No request reaches Strava."""
import os
import sys
import tempfile
import unittest
import logging
from pathlib import Path
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch, Mock
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
temporary = tempfile.TemporaryDirectory(prefix="november-tests-")
unittest.addModuleCleanup(temporary.cleanup)
test_url = os.getenv("TEST_DATABASE_URL", "sqlite:///" + str(Path(temporary.name) / "test.db"))
if "test" not in urlparse(test_url).path.lower():
    raise RuntimeError("TEST_DATABASE_URL must name a disposable database containing 'test'")
os.environ.update(DATABASE_URL=test_url, ENABLE_BACKGROUND_SYNC="0", ENABLE_DEBUG_ROUTES="0", REQUIRE_POSTGRES="0",
    ADMIN_PASSWORD="local-test-password", FRONTEND_URL="http://localhost:5173", CHALLENGE_YEAR="2026", COOKIE_SECURE="0",
    STRAVA_CLIENT_ID="123", STRAVA_CLIENT_SECRET="test-only", STRAVA_WEBHOOK_VERIFY_TOKEN="verify-test", STRAVA_WEBHOOK_SUBSCRIPTION_ID="1234",
    CHALLENGE_TEST_MODE="0", CHALLENGE_TEST_START_DATE="", CHALLENGE_TEST_PERIOD_DAYS="", LOAD_ENV_FILE="0", STRAVA_SYNC_ENABLED="1")

from fastapi.testclient import TestClient
import main
from database import Base, engine, SessionLocal
from models.user import User
from models.activity import Activity
from models.claim import Claim
from models.challenge import ChallengeClaim, DistanceTarget
from models.session import AuthSession, OAuthState
from models.community import CommunityRun
from services import challenge, strava
from services.sessions import issue_session, digest
from services.time import utcnow

logging.getLogger("httpx").setLevel(logging.WARNING)
unittest.addModuleCleanup(engine.dispose)

DRAW = [5, 6, 9, 14, 27, 19, 24, 29]

def reply(data, status=200):
    result = Mock(status_code=status)
    result.json.return_value = data
    if status >= 400:
        import requests
        result.raise_for_status.side_effect = requests.HTTPError()
    return result

def run_data(sid, km, day=1, **extra):
    return {"id": sid, "distance": km * 1000, "start_date": f"2026-11-{day:02d}T08:00:00Z", "sport_type": "Run", "athlete": {"id": 99}, **extra}

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(main.DB_AVAILABLE)
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            challenge.seed(db)
        self.today = self.enterContext(patch("services.challenge.local_today", return_value=date(2026, 11, 4)))
        self.enterContext(patch("routes.admin.local_today", return_value=date(2026, 12, 1)))
        self.enterContext(patch("requests.sessions.Session.request", side_effect=AssertionError("Unexpected network request")))
        self.client = self.enterContext(TestClient(main.app))
        response = self.client.post("/admin/login", json={"password": "local-test-password"})
        self.assertEqual(response.status_code, 200, response.text)
        self.admin = {"X-Admin-Token": response.json()["token"]}

    def add_user(self, name="Sofia Example", strava_id=None):
        with SessionLocal() as db:
            u = User(name=name, strava_id=strava_id, access_token="strava-secret" if strava_id else None,
                refresh_token="refresh-secret" if strava_id else None, token_expires_at=2100000000)
            db.add(u); db.commit()
            return u.id

    def authorize(self, uid, client=None):
        with SessionLocal() as db:
            token = issue_session(db, user_id=uid); db.commit()
        (client or self.client).cookies.set("nc_session", token)
        return token

    def publish(self, number=1, distances=DRAW):
        response = self.client.post(f"/admin/challenge/periods/{number}/publish", headers=self.admin, json={"distances": distances})
        self.assertEqual(response.status_code, 200, response.text)

    def add_run(self, uid, km, day, manual=False, sid=None):
        self.today.return_value = max(self.today.return_value, date(2026, 11, day))
        with SessionLocal() as db:
            e, _ = challenge.lock_user(db, uid)
            a = Activity(user_id=uid, date=date(2026, 11, day), distance_km=km, is_manual=manual, strava_id=str(sid) if sid else None, status="pending")
            db.add(a); db.flush(); aid = a.id
            challenge.rebuild_user(db, uid, e); db.commit()
            return aid

    def result(self, uid):
        return next(u for u in self.client.get("/users/").json() if u["id"] == uid)

    def body(self):
        return {"name": "Elias", "distance_km": 9, "pace_seconds": 360, "starts_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "latitude": 47.37, "longitude": 8.54, "meeting_point": "Beim Bahnhof"}

    def october(self):
        self.enterContext(patch.dict(os.environ, CHALLENGE_TEST_MODE="1", CHALLENGE_TEST_START_DATE="2026-10-01"))
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            challenge.seed(db)
        self.today.return_value = date(2026, 10, 7)
        self.admin = {"X-Admin-Token": self.client.post("/admin/login", json={"password": "local-test-password"}).json()["token"]}

    def test_production_calendar_unchanged_and_rejects_test_database_reuse(self):
        from services.schedule import ScheduleConfigurationError
        config = self.client.get("/challenge").json()
        self.assertFalse(config["test_mode"])
        self.assertEqual((config["starts_on"], config["finale_date"]), ("2026-11-01", "2026-11-30"))
        self.assertEqual([p["capacity"] for p in config["periods"]], [8, 7, 7, 7])
        self.assertEqual(self.client.put("/admin/challenge/test-calendar", headers=self.admin,
            json={"starts_on": "2026-10-01", "period_days": [8, 7, 7, 7]}).status_code, 403)
        with patch.dict(os.environ, CHALLENGE_TEST_MODE="1"):
            with SessionLocal() as db:
                with self.assertRaises(ScheduleConfigurationError): challenge.seed(db)
        after = self.client.get("/challenge").json()
        self.assertEqual({k: v for k, v in after.items() if k != "server_now"},
                         {k: v for k, v in config.items() if k != "server_now"})

    def test_october_import_scorer_admin_and_chart_share_calendar(self):
        self.october(); self.publish(); uid = self.add_user(strava_id=99)
        data = [run_data(11, 35, 1), run_data(12, 10, 1), run_data(13, 30, 2), run_data(14, 7, 3), run_data(15, 4, 4)]
        data = [{**a, "start_date": a["start_date"].replace("-11-", "-10-")} for a in data]
        with SessionLocal() as db:
            outside = Activity(user_id=uid, date=date(2026, 11, 1), distance_km=35, strava_id="900", status="pending")
            db.add(outside); db.commit()
        with patch("services.strava.requests.get", return_value=reply(data)) as request:
            with SessionLocal() as db: strava.sync_user(db, uid)
        from services.time import ZURICH
        params = request.call_args.kwargs["params"]
        self.assertEqual(params["after"], int(datetime(2026, 10, 1, tzinfo=ZURICH).timestamp()) - 1)
        self.assertEqual(params["before"], int(datetime(2026, 10, 31, tzinfo=ZURICH).timestamp()))
        self.assertEqual(self.result(uid)["total_score"], 62)
        self.assertEqual(self.result(uid)["completed_count"], 3)
        self.assertEqual(self.result(uid)["cells"][14]["finale_date"], "2026-10-30")
        stats = self.client.get("/challenge/statistics").json()
        self.assertEqual((stats["points"][0]["date"], stats["points"][-1]["date"]), ("2026-10-01", "2026-10-30"))
        self.assertEqual(stats["total_km"], 62)
        activities = self.client.get("/admin/activities", headers=self.admin).json()
        self.assertEqual(len(activities), 5)
        self.assertTrue(all(a["date"].startswith("2026-10-") for a in activities))
        with SessionLocal() as db:
            self.assertEqual(db.query(Activity).filter_by(strava_id="900").one().status, "pending")

    def test_short_october_rehearsal_week_changes_and_finale(self):
        self.october()
        change = self.client.put("/admin/challenge/test-calendar", headers=self.admin,
            json={"starts_on": "2026-10-01", "period_days": [1, 1, 1, 1]})
        self.assertEqual(change.status_code, 200, change.text)
        self.assertEqual(change.json()["finale_date"], "2026-10-05")
        self.publish()
        self.publish(2, [1, 2, 3, 4, 7, 8, 10])
        self.publish(3, [11, 12, 13, 16, 17, 18, 20])
        self.publish(4, [21, 22, 23, 25, 26, 28, 30])
        uid = self.add_user(strava_id=99)
        data = [{**run_data(100 + day, km, day), "start_date": f"2026-10-{day:02d}T08:00:00Z"} for day, km in [(1, 35), (2, 35), (3, 35), (4, 35), (5, 15)]]
        self.today.return_value = date(2026, 10, 4)
        with patch("services.strava.requests.get", return_value=reply(data)):
            with SessionLocal() as db: strava.sync_user(db, uid)
        self.assertEqual(self.result(uid)["total_score"], 89)  # No future finale credit.
        self.today.return_value = date(2026, 10, 7)
        with SessionLocal() as db:
            challenge.rebuild_user(db, uid); db.commit()
        self.assertEqual(self.result(uid)["total_score"], 104)
        self.assertEqual(self.result(uid)["cells"][14]["status"], "completed")
        self.assertEqual(len(self.client.get("/challenge/statistics").json()["points"]), 5)
        self.assertEqual(self.client.put("/admin/challenge/test-calendar", headers=self.admin,
            json={"starts_on": "2026-10-02", "period_days": [1, 1, 1, 1]}).status_code, 409)
        self.assertEqual(self.client.put("/admin/challenge/finale", headers=self.admin, json={"km": 16}).status_code, 409)
        with SessionLocal() as db: challenge.seed(db)  # Restart keeps the saved calendar.
        self.assertEqual(self.client.get("/challenge").json()["finale_date"], "2026-10-05")

    def test_test_calendar_validation_and_manual_date_bounds(self):
        self.october()
        for body in ({"starts_on": "2026-12-29", "period_days": [8, 7, 7, 7]},
                     {"starts_on": "2026-10-01", "period_days": [0, 7, 7, 7]},
                     {"starts_on": "2026-10-01", "period_days": [True, 7, 7, 7]},
                     {"starts_on": "2026-10-01", "period_days": [8, 7, 7]}):
            self.assertEqual(self.client.put("/admin/challenge/test-calendar", headers=self.admin, json=body).status_code, 422)
        uid = self.add_user()
        response = self.client.post("/admin/activities", headers=self.admin,
            json={"user_id": uid, "date": "2026-09-30", "distance_km": 35})
        self.assertEqual(response.status_code, 422)

    def test_test_database_cannot_be_reopened_as_production(self):
        self.october()
        from services.schedule import ScheduleConfigurationError
        with patch.dict(os.environ, CHALLENGE_TEST_MODE="0", CHALLENGE_TEST_START_DATE=""):
            with SessionLocal() as db:
                with self.assertRaises(ScheduleConfigurationError): challenge.seed(db)

    def test_test_settings_require_explicit_test_mode(self):
        from services.schedule import ScheduleConfigurationError, initial_calendar
        with patch.dict(os.environ, CHALLENGE_TEST_START_DATE="2026-10-01"):
            with self.assertRaises(ScheduleConfigurationError): initial_calendar(2026, False)

    def test_paused_strava_disables_scheduler_manual_import_and_webhook_worker(self):
        uid = self.add_user(strava_id=99); self.authorize(uid)
        with patch.dict(os.environ, STRAVA_SYNC_ENABLED="0"), patch("services.strava.api_get") as request:
            strava.sync_user_background(uid)
            strava.sync_all_background()
            strava.webhook_background(99, 9, "update")
            request.assert_not_called()
            self.assertEqual(self.client.post("/users/me/sync").status_code, 409)
            self.assertEqual(self.client.post("/admin/sync", headers=self.admin).status_code, 409)
            self.assertTrue(self.client.get("/users/me").json()["sync_paused"])
            self.assertFalse(self.client.get("/challenge").json()["strava_sync_enabled"])

    def test_sync_http_diagnostics_hide_credentials_and_preserve_claims(self):
        import requests
        self.publish(); uid = self.add_user(strava_id=99); self.add_run(uid, 35, 1, sid=900)
        self.authorize(uid)
        response = requests.Response()
        response.status_code = 403
        response.url = "https://www.strava.com/api/v3/athlete/activities?access_token=must-not-log"
        response._content = b'{"secret":"must-not-log"}'
        with patch("services.strava.requests.get", return_value=response), self.assertLogs("services.strava", level="WARNING") as logs:
            strava.sync_user_background(uid)
        self.assertIn("status=403 endpoint=/api/v3/athlete/activities", logs.output[0])
        self.assertNotIn("must-not-log", " ".join(logs.output))
        self.assertEqual(self.result(uid)["total_score"], 29)
        self.assertIn("Freigabe", self.client.get("/users/me").json()["sync_error"])

    def test_migration_upgrades_existing_weekly_edition_without_changing_dates(self):
        from sqlalchemy import create_engine, text, inspect
        import migrations
        legacy = create_engine("sqlite:///" + str(Path(temporary.name) / "weekly-test.db"))
        with legacy.begin() as conn:
            conn.execute(text("CREATE TABLE schema_migrations (revision VARCHAR(80) PRIMARY KEY)"))
            conn.execute(text("INSERT INTO schema_migrations VALUES ('2026_02_weekly')"))
            conn.execute(text("CREATE TABLE challenge_editions (id INTEGER PRIMARY KEY, year INTEGER UNIQUE, timezone VARCHAR, finale_km INTEGER)"))
            conn.execute(text("INSERT INTO challenge_editions VALUES (1,2026,'Europe/Zurich',15)"))
        with patch("migrations.engine", legacy):
            migrations.migrate(); migrations.migrate()
        with legacy.connect() as conn:
            self.assertEqual(conn.scalar(text("SELECT year FROM challenge_editions")), 2026)
            self.assertFalse(conn.scalar(text("SELECT is_test FROM challenge_editions")))
            self.assertIsNone(conn.scalar(text("SELECT finale_on FROM challenge_editions")))
            self.assertIn("finale_on", {c["name"] for c in inspect(conn).get_columns("challenge_editions")})
        legacy.dispose()

    def test_public_contract_and_no_credentials(self):
        uid = self.add_user(strava_id=99)
        self.assertEqual(self.client.get("/healthz").status_code, 200)
        self.assertEqual(self.client.get("/users/me").status_code, 401)
        self.assertEqual(self.client.get("/users/me?access_token=strava-secret", headers={"Authorization": "Bearer strava-secret"}).status_code, 401)
        public = self.client.get("/users/")
        self.assertNotIn("secret", public.text)
        self.assertNotIn("strava_id", public.text)
        self.assertEqual(len(self.result(uid)["cells"]), 30)
        self.assertEqual(self.client.get("/challenge").json()["finale_km"], 15)

    def test_admin_and_origin_guards(self):
        for path in ("/admin/users", "/admin/activities", "/admin/challenge", "/admin/community"):
            self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.post("/admin/sync").status_code, 401)
        self.assertEqual(self.client.post("/admin/login", json={"password": "wrong"}).status_code, 401)
        self.assertEqual(self.client.post("/auth/logout", headers={"Origin": "https://evil.example"}).status_code, 403)
        r = self.client.options("/community", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Content-Type"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["access-control-allow-credentials"], "true")

    def test_exact_scoring_examples(self):
        self.publish(); uid = self.add_user()
        for km, day in [(35, 1), (30, 2), (7, 3), (4, 4)]: self.add_run(uid, km, day)
        result = self.result(uid)
        self.assertEqual(result["total_score"], 62)
        self.assertEqual([c["km"] for c in result["cells"] if c["status"] == "completed"], [6, 27, 29])
        self.assertEqual(result["cells"][4]["status"], "open")

    def test_longest_run_only_and_late_upload_reorders_results(self):
        self.publish(); uid = self.add_user()
        self.add_run(uid, 30, 2)
        self.add_run(uid, 7, 3)
        self.add_run(uid, 35, 1)  # uploaded later, but must claim 29 first
        self.add_run(uid, 20, 1)
        self.add_run(uid, 3, 3)
        result = self.result(uid)
        self.assertEqual(result["total_score"], 62)
        with SessionLocal() as db:
            claims = db.query(ChallengeClaim).order_by(ChallengeClaim.date).all()
            self.assertEqual([c.km for c in claims], [29, 27, 6])
            challenge.rebuild_user(db, uid); db.commit()
            self.assertEqual(db.query(ChallengeClaim).count(), 3)

    def test_no_round_up_and_no_accumulation(self):
        self.publish(); uid = self.add_user()
        self.add_run(uid, 4.999999, 1); self.add_run(uid, 4, 1)
        self.assertEqual(self.result(uid)["total_score"], 0)
        self.add_run(uid, 5, 2)
        self.assertEqual(self.result(uid)["total_score"], 5)

    def test_future_activity_is_not_scored_early(self):
        self.publish(); uid = self.add_user()
        with SessionLocal() as db:
            db.add(Activity(user_id=uid, date=date(2026, 11, 5), distance_km=35, is_manual=False, status="pending"))
            db.flush(); challenge.rebuild_user(db, uid); db.commit()
        self.assertEqual(self.result(uid)["total_score"], 0)
        self.today.return_value = date(2026, 11, 5)
        with SessionLocal() as db:
            challenge.rebuild_user(db, uid); db.commit()
        self.assertEqual(self.result(uid)["total_score"], 29)

    def test_drafts_private_unique_and_finale_reserved(self):
        r = self.client.put("/admin/challenge/periods/1", headers=self.admin, json={"distances": DRAW})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get("/challenge").json()["periods"][0]["distances"], [])
        for values in ([1] * 8, [1, 2, 3, 4, 5, 6, 7, 15], [1, 2, 3, 4, 5, 6, 7, 31], [1.0, 2, 3, 4, 5, 6, 7, 8]):
            self.assertEqual(self.client.put("/admin/challenge/periods/1", headers=self.admin, json={"distances": values}).status_code, 422)
        self.assertEqual(self.client.put("/admin/challenge/periods/2", headers=self.admin, json={"distances": [5, 1, 2, 3, 4, 7, 8]}).status_code, 422)
        uid = self.add_user(); self.add_run(uid, 35, 1)
        self.assertEqual(self.result(uid)["total_score"], 0)
        self.publish()
        self.assertEqual(self.result(uid)["total_score"], 29)

    def test_published_period_freezes_and_future_draw_can_change(self):
        self.publish()
        self.assertEqual(self.client.put("/admin/challenge/periods/1", headers=self.admin, json={"distances": DRAW}).status_code, 409)
        second = [1, 2, 3, 4, 7, 8, 10]
        self.publish(2, second)
        self.assertEqual(self.client.put("/admin/challenge/periods/2", headers=self.admin, json={"distances": second}).status_code, 200)
        self.assertFalse(self.client.get("/challenge").json()["periods"][1]["published"])

    def test_no_week_carryover_and_finale_only_nov30(self):
        self.publish(); self.publish(2, [1, 2, 3, 4, 7, 8, 10]); uid = self.add_user()
        self.add_run(uid, 50, 8); self.add_run(uid, 50, 9); self.add_run(uid, 15, 29)
        self.assertEqual(self.result(uid)["total_score"], 39)
        self.add_run(uid, 14.999, 30)
        self.assertEqual(self.result(uid)["total_score"], 39)
        self.add_run(uid, 15, 30)
        self.assertEqual(self.result(uid)["total_score"], 54)

    def test_finale_config_and_full_season_465(self):
        self.assertEqual(self.client.put("/admin/challenge/finale", headers=self.admin, json={"km": 30}).status_code, 200)
        self.assertEqual(self.client.get("/challenge").json()["finale_km"], 30)
        values = list(range(1, 30))
        day = 1; uid = self.add_user()
        for number, size in enumerate([8, 7, 7, 7], 1):
            draw, values = values[:size], values[size:]
            self.publish(number, draw)
            for _ in range(size): self.add_run(uid, 50, day); day += 1
        self.add_run(uid, 30, 30)
        self.assertEqual(self.result(uid)["total_score"], 465)
        self.assertEqual(self.result(uid)["completed_count"], 30)

    def test_manual_override_delete_restores_strava_and_old_results_unchanged(self):
        self.publish(); uid = self.add_user(); sid = self.add_run(uid, 35, 1, sid=9)
        with SessionLocal() as db:
            u = db.get(User, uid); u.total_score = 465; u.slots = list(range(1, 31))
            db.add(Claim(user_id=uid, km=30, date=date(2025, 11, 1))); db.commit()
        r = self.client.post("/admin/activities", headers=self.admin, json={"user_id": uid, "date": "2026-11-01", "distance_km": 7})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.result(uid)["total_score"], 6)
        self.client.delete(f"/admin/activities/{r.json()['id']}", headers=self.admin)
        self.assertEqual(self.result(uid)["total_score"], 29)
        with SessionLocal() as db:
            self.assertEqual(db.get(User, uid).total_score, 465)
            self.assertEqual(db.query(Claim).first().km, 30)
        self.client.delete(f"/admin/activities/{sid}", headers=self.admin)
        self.assertEqual(self.result(uid)["total_score"], 0)
        self.assertEqual(self.client.post(f"/admin/activities/{sid}/restore", headers=self.admin).status_code, 200)
        self.assertEqual(self.result(uid)["total_score"], 29)

    def test_ties_and_statistics_use_credited_km(self):
        self.publish(); a, b, c = self.add_user("A"), self.add_user("B"), self.add_user("C")
        for uid in [a, b]: self.add_run(uid, 35, 1)
        self.add_run(c, 7, 2)
        self.assertEqual([p["rank"] for p in self.client.get("/users/").json()], [1, 1, 3])
        stats = self.client.get("/challenge/statistics").json()
        self.assertEqual(stats["total_km"], 64)
        self.assertEqual(stats["points"][0]["daily_km"], 58)
        self.assertEqual(stats["points"][1]["total_km"], 64)

    def test_sessions_persist_independently_of_strava_tokens(self):
        uid = self.add_user(strava_id=99); token = self.authorize(uid)
        with SessionLocal() as db:
            u = db.get(User, uid); u.access_token = "rotated"; u.refresh_token = "rotated-refresh"; db.commit()
            self.assertIsNotNone(db.get(AuthSession, digest(token)))
        with TestClient(main.app) as other:
            other.cookies.set("nc_session", token)
            self.assertEqual(other.get("/users/me").json()["id"], uid)
            self.assertEqual(other.post("/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/users/me").status_code, 401)

    def test_expired_sessions_and_sliding_cookie(self):
        uid = self.add_user(); token = self.authorize(uid)
        with SessionLocal() as db:
            s = db.get(AuthSession, digest(token)); s.expires_at = utcnow() + timedelta(days=10); db.commit()
        response = self.client.get("/users/me")
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("SameSite=lax", response.headers["set-cookie"])
        with SessionLocal() as db:
            s = db.get(AuthSession, digest(token)); s.expires_at = utcnow() - timedelta(seconds=1); db.commit()
        self.assertEqual(self.client.get("/users/me").status_code, 401)

    def test_oauth_state_and_no_browser_tokens(self):
        response = self.client.get("/auth/login?return_to=//evil.example", follow_redirects=False)
        state = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
        self.assertEqual(self.client.get("/auth/callback?code=abc&state=wrong").status_code, 400)
        data = {"athlete": {"id": 99, "firstname": "Sofia", "lastname": "Example"}, "access_token": "secret-access", "refresh_token": "secret-refresh", "expires_at": 2100000000}
        with patch("auth.routes.requests.post", return_value=reply(data)), patch("services.strava.sync_user_background"):
            callback = self.client.get("/auth/callback", params={"code": "abc", "state": state}, follow_redirects=False)
        self.assertEqual(callback.status_code, 303)
        self.assertEqual(callback.headers["location"], "http://localhost:5173/")
        self.assertNotIn("secret", callback.text + str(callback.headers))
        self.assertEqual(self.client.get("/users/me").json()["name"], "Sofia Example")
        self.assertEqual(self.client.get("/auth/callback", params={"code": "abc", "state": state}).status_code, 400)

    def test_guest_create_join_leave_ownership_and_cancel(self):
        created = self.client.post("/community", json=self.body())
        self.assertEqual(created.status_code, 201, created.text)
        run = created.json(); rid = run["id"]
        self.assertEqual(run["participants"], ["Elias"])
        self.assertTrue(run["can_manage"])
        with TestClient(main.app) as guest:
            guest.get("/community")
            self.assertEqual(guest.delete(f"/community/{rid}").status_code, 403)
            for _ in range(2): self.assertEqual(guest.post(f"/community/{rid}/participants", json={"name": "Alex"}).status_code, 200)
            self.assertEqual(guest.get("/community").json()["runs"][0]["participants"].count("Alex"), 1)
            self.assertTrue(guest.get("/community").json()["runs"][0]["can_leave"])
            self.assertEqual(guest.delete(f"/community/{rid}/participants/me").status_code, 200)
        self.assertEqual(self.client.delete(f"/community/{rid}/participants/me").status_code, 409)
        self.assertEqual(self.client.delete(f"/community/{rid}").status_code, 200)
        self.assertEqual(self.client.get("/community").json()["runs"], [])

    def test_guest_ownership_survives_login_and_reload(self):
        rid = self.client.post("/community", json=self.body()).json()["id"]
        self.authorize(self.add_user())
        self.assertTrue(self.client.get("/community").json()["runs"][0]["can_manage"])
        body = {**self.body(), "meeting_point": "Beim Brunnen"}
        self.assertEqual(self.client.put(f"/community/{rid}", json=body).status_code, 200)
        self.assertNotIn("identity", self.client.get("/community").text)

    def test_expiry_exactly_three_hours_and_timezone_validation(self):
        body = self.body(); body["starts_at"] = (datetime.now(timezone.utc) + timedelta(days=1)).astimezone(timezone(timedelta(hours=1))).isoformat()
        created = self.client.post("/community", json=body).json()
        expiry = datetime.fromisoformat(created["expires_at"].replace("Z", "+00:00")).replace(tzinfo=None)
        with patch("routes.community.utcnow", return_value=expiry - timedelta(microseconds=1)):
            self.assertEqual(len(self.client.get("/community").json()["runs"]), 1)
        with patch("routes.community.utcnow", return_value=expiry):
            self.assertEqual(self.client.get("/community").json()["runs"], [])
            self.assertEqual(self.client.post(f"/community/{created['id']}/participants", json={"name": "Late"}).status_code, 404)
        for change in ({"starts_at": "2026-11-04T18:00:00"}, {"latitude": 95}, {"name": "   "}, {"pace_seconds": 0}, {"distance_km": -1}):
            self.assertEqual(self.client.post("/community", json={**self.body(), **change}).status_code, 422)

    def test_community_rate_limit_is_persistent(self):
        for _ in range(5): self.assertEqual(self.client.post("/community", json=self.body()).status_code, 201)
        with TestClient(main.app) as new_client:
            self.assertEqual(new_client.post("/community", json=self.body()).status_code, 429)

    def test_account_deletion_preserves_guest_group_and_revokes_login(self):
        uid = self.add_user(); token = self.authorize(uid)
        rid = self.client.post("/community", json=self.body()).json()["id"]
        self.assertEqual(self.client.delete(f"/admin/users/{uid}", headers=self.admin).status_code, 200)
        self.assertEqual(self.client.get("/users/me").status_code, 401)
        self.assertTrue(self.client.get("/community").json()["runs"][0]["can_manage"])
        with SessionLocal() as db:
            self.assertIsNone(db.get(AuthSession, digest(token)))
            self.assertIsNone(db.get(CommunityRun, rid).user_id)

    def test_migration_adds_columns_and_preserves_legacy_results(self):
        from sqlalchemy import create_engine, text, inspect
        import migrations
        legacy = create_engine("sqlite:///" + str(Path(temporary.name) / "legacy-test.db"))
        with legacy.begin() as conn:
            conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR, strava_id VARCHAR UNIQUE, access_token VARCHAR, refresh_token VARCHAR, total_score INTEGER)"))
            conn.execute(text("INSERT INTO users (id,name,strava_id,total_score) VALUES (1,'Historical','99',465)"))
            conn.execute(text("CREATE TABLE activities (id INTEGER PRIMARY KEY, user_id INTEGER, strava_id VARCHAR UNIQUE, date DATE, distance_km FLOAT, effective_km INTEGER, status VARCHAR)"))
            conn.execute(text("INSERT INTO activities (id,user_id,date,distance_km,effective_km,status) VALUES (1,1,'2025-11-01',30,30,'claimed')"))
        with patch("migrations.engine", legacy):
            migrations.migrate(); migrations.migrate()
        with legacy.connect() as conn:
            self.assertEqual(conn.scalar(text("SELECT total_score FROM users WHERE id=1")), 465)
            self.assertEqual(conn.scalar(text("SELECT effective_km FROM activities WHERE id=1")), 30)
            self.assertIn("token_expires_at", {c["name"] for c in inspect(conn).get_columns("users")})
            self.assertIn("challenge_claims", inspect(conn).get_table_names())
        legacy.dispose()

    def test_webhook_verification_and_quick_background_dispatch(self):
        response = self.client.get("/auth/webhook", params={"hub.mode": "subscribe", "hub.challenge": "abc", "hub.verify_token": "verify-test"})
        self.assertEqual(response.json(), {"hub.challenge": "abc"})
        event = {"subscription_id": 1234, "object_type": "activity", "object_id": 9, "owner_id": 99, "aspect_type": "delete"}
        with patch("services.strava.webhook_background") as worker:
            self.assertEqual(self.client.post("/auth/webhook", json=event).status_code, 200)
            worker.assert_called_once_with(99, 9, "delete")
        self.assertEqual(self.client.post("/auth/webhook", json={**event, "subscription_id": 0}).status_code, 403)

    def test_sync_uses_same_scorer_reconciles_deletions_and_is_idempotent(self):
        self.publish(); uid = self.add_user(strava_id=99)
        data = [run_data(11, 35, 1), run_data(12, 30, 2), run_data(13, 7, 3), run_data(14, 4, 4)]
        with patch("services.strava.requests.get", return_value=reply(data)):
            for _ in range(2):
                with SessionLocal() as db: strava.sync_user(db, uid)
        self.assertEqual(self.result(uid)["total_score"], 62)
        with SessionLocal() as db: self.assertEqual(db.query(Activity).count(), 4)
        with patch("services.strava.requests.get", return_value=reply(data[1:])):
            with SessionLocal() as db: strava.sync_user(db, uid)
        self.assertEqual(self.result(uid)["total_score"], 35)  # 30->29 and 7->6

    def test_strava_refresh_and_zurich_date(self):
        uid = self.add_user(strava_id=99)
        with SessionLocal() as db:
            u = db.get(User, uid); u.token_expires_at = 1; db.commit()
        token_data = {"access_token": "new-access", "refresh_token": "new-refresh", "expires_at": 2100000000}
        with patch("services.strava.requests.post", return_value=reply(token_data)):
            with SessionLocal() as db:
                self.assertEqual(strava.access_token(db, uid), "new-access")
                self.assertEqual(db.get(User, uid).refresh_token, "new-refresh")
        self.assertEqual(strava.normalized(run_data(9, 5, start_date="2026-10-31T23:30:00Z"))["date"], date(2026, 11, 1))
        self.assertIsNone(strava.normalized(run_data(9, 5, sport_type="Ride")))

    def test_revoked_strava_token_keeps_website_session_and_prompts_reconnect(self):
        uid = self.add_user(strava_id=99); self.authorize(uid)
        error = {"errors": [{"field": "refresh_token", "code": "invalid"}]}
        with patch("services.strava.requests.post", return_value=reply(error, 400)):
            with SessionLocal() as db:
                with self.assertRaises(Exception): strava.access_token(db, uid, force=True)
        response = self.client.get("/users/me")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["strava_connected"])

    def test_pagination_and_failed_import_does_not_remove_results(self):
        self.publish(); uid = self.add_user(strava_id=99); self.add_run(uid, 35, 1, sid=900)
        first = [run_data(1000 + i, 5, 1) for i in range(200)]
        with patch("services.strava.requests.get", side_effect=[reply(first), reply([run_data(2001, 30, 2)])]) as request:
            with SessionLocal() as db: strava.sync_user(db, uid)
            self.assertEqual(request.call_args_list[1].kwargs["params"]["page"], 2)
        before = self.result(uid)["total_score"]
        with patch("services.strava.requests.get", side_effect=[reply(first), reply({}, 503)]):
            with SessionLocal() as db:
                with self.assertRaises(Exception): strava.sync_user(db, uid)
        self.assertEqual(self.result(uid)["total_score"], before)

    def test_webhook_deletion_fetches_strava_and_recalculates(self):
        self.publish(); uid = self.add_user(strava_id=99); self.add_run(uid, 35, 1, sid=9); self.add_run(uid, 30, 2, sid=10)
        with patch("services.strava.requests.get", return_value=reply({}, 404)):
            strava.webhook_background(99, 9, "delete")
        self.assertEqual(self.result(uid)["total_score"], 29)

    @unittest.skipUnless(engine.dialect.name == "postgresql", "PostgreSQL locking test")
    def test_concurrent_claim_rebuild_and_duplicate_guest_join(self):
        self.publish(); uid = self.add_user(); self.add_run(uid, 35, 1)
        def rebuild(_):
            with SessionLocal() as db: challenge.rebuild_user(db, uid); db.commit()
        with ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(rebuild, range(8)))
        self.assertEqual(self.result(uid)["completed_count"], 1)
        with SessionLocal() as db: self.assertEqual(db.query(ChallengeClaim).count(), 1)
        rid = self.client.post("/community", json=self.body()).json()["id"]
        with TestClient(main.app) as guest:
            guest.get("/community")
            cookies = dict(guest.cookies)
        def join(_):
            with TestClient(main.app) as client:
                client.cookies.update(cookies)
                return client.post(f"/community/{rid}/participants", json={"name": "Parallel Guest"}).status_code
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(join, range(8))), [200] * 8)
        self.assertEqual(self.client.get("/community").json()["runs"][0]["participants"].count("Parallel Guest"), 1)

if __name__ == "__main__":
    unittest.main()
