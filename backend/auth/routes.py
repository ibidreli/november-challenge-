from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from dotenv import load_dotenv
import os
from urllib.parse import urlencode

# added imports
import requests
from sqlalchemy.orm import Session
from database import get_db  # ensure get_db available for debug route
from models.user import User
import logging
import traceback
import datetime
import os

# load .env only when explicitly requested (avoid accidentally overriding Render env vars)
if os.getenv("LOAD_ENV_FILE", "0") == "1":
    load_dotenv()

router = APIRouter()

# add: use CHALLENGE_MONTH env (default 11)
CHALLENGE_MONTH = int(os.getenv("CHALLENGE_MONTH", "11"))


def build_strava_auth_url(request: Request | None = None):
    client_id = os.getenv("STRAVA_CLIENT_ID")
    redirect_uri_env = os.getenv("STRAVA_REDIRECT_URI") or ""

    # Treat localhost/127.0.0.1 values as invalid in production and ignore them.
    if redirect_uri_env.strip() and not ("localhost" in redirect_uri_env or "127.0.0.1" in redirect_uri_env):
        redirect_uri = redirect_uri_env
    else:
        if redirect_uri_env.strip():
            # warn that an invalid localhost value was present and is being ignored
            logging.warning("Ignoring STRAVA_REDIRECT_URI because it points to localhost/127.0.0.1. Will use request base_url instead.")
        if request is not None:
            # build redirect from current request base (keeps https when using ngrok / public domain)
            redirect_uri = str(request.base_url).rstrip("/") + "/auth/callback"
        else:
            # no env and no request -> cannot build a usable redirect
            logging.error("No valid STRAVA_REDIRECT_URI env and no request base available to build redirect_uri.")
            redirect_uri = ""

    scope = os.getenv("STRAVA_SCOPE", "read,activity:read_all")
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "approval_prompt": "auto",
        "scope": scope,
    }
    # debug log which redirect_uri will be used (helps diagnose localhost redirects)
    logging.info("build_strava_auth_url -> using redirect_uri: %s", redirect_uri)
    # If redirect_uri is empty, return empty string so caller can handle the error cleanly
    if not redirect_uri:
        return ""
    return "https://www.strava.com/oauth/authorize?" + urlencode(params)


def _invalid_client_config():
    cid = os.getenv("STRAVA_CLIENT_ID")
    csec = os.getenv("STRAVA_CLIENT_SECRET")
    if not cid or cid.strip() == "" or cid.strip().startswith("<") or not cid.isdigit():
        return True, "STRAVA_CLIENT_ID fehlt oder ist ungültig (muss eine Zahl ohne spitze Klammern sein)."
    if not csec or csec.strip() == "" or csec.strip().startswith("<"):
        return True, "STRAVA_CLIENT_SECRET fehlt oder ist offensichtlich nicht gesetzt."
    return False, None


# helper: sync recent activities from Strava (since last Monday)
def sync_recent_activities_from_strava(user: User, db: Session):
	"""
	Fetch activities for the authenticated user from Strava starting from the
	first day of CHALLENGE_MONTH (current year or previous year if month not yet reached),
	insert new Activity rows and process them using the app's processing helper.
	Returns summary dict.
	"""
	from models.activity import Activity as ActivityModel
	# import processing helper locally to avoid circular imports
	try:
		from routes.activities import process_activity_instance, CHALLENGE_MONTH as ROUTE_CHALLENGE_MONTH
	except Exception:
		from backend.routes.activities import process_activity_instance, CHALLENGE_MONTH as ROUTE_CHALLENGE_MONTH

	STRAVA_API_ACTIVITIES = "https://www.strava.com/api/v3/athlete/activities"
	if not user or not user.access_token:
		logging.info("No user or access_token for sync.")
		return {"synced": 0, "reason": "no_token"}

	# compute start = first day of CHALLENGE_MONTH
	today = datetime.date.today()
	month = CHALLENGE_MONTH if CHALLENGE_MONTH else ROUTE_CHALLENGE_MONTH
	# pick year: if current month >= target month -> current year, else previous year
	year = today.year if today.month >= month else today.year - 1
	start_date = datetime.date(year, month, 1)
	# start of day -> epoch seconds
	since_dt = datetime.datetime.combine(start_date, datetime.time.min)
	since_epoch = int(since_dt.timestamp())

	headers = {"Authorization": f"Bearer {user.access_token}"}
	per_page = 200
	page = 1
	synced = 0
	try:
		while True:
			params = {"after": since_epoch, "per_page": per_page, "page": page}
			r = requests.get(STRAVA_API_ACTIVITIES, headers=headers, params=params, timeout=15)
			if r.status_code == 401:
				# token invalid/expired — stop and surface the issue
				logging.warning("Unauthorized when fetching activities for user %s", user.id)
				return {"synced": synced, "error": "unauthorized"}
			r.raise_for_status()
			activities = r.json() or []
			if not activities:
				break
			for a in activities:
				try:
					strava_aid = str(a.get("id"))
					# skip if already stored
					exists = db.query(ActivityModel).filter(ActivityModel.strava_id == strava_aid).first()
					if exists:
						continue
					distance_m = a.get("distance") or 0
					distance_km = float(distance_m) / 1000.0
					start = a.get("start_date_local") or a.get("start_date")
					if not start:
						continue
					if start.endswith("Z"):
						start = start[:-1]
					dt = datetime.datetime.fromisoformat(start)
					act_date = dt.date()
					# insert Activity
					activity_obj = ActivityModel(user_id=user.id, strava_id=strava_aid, date=act_date, distance_km=distance_km, status="fetched")
					db.add(activity_obj)
					db.commit()
					db.refresh(activity_obj)
					# process using helper (use CHALLENGE_MONTH env if set)
					simulate_month = int(os.getenv("CHALLENGE_MONTH")) if os.getenv("CHALLENGE_MONTH") else None
					try:
						process_activity_instance(activity_obj, db, simulate_month=simulate_month)
					except Exception:
						logging.exception("Processing activity failed for %s", strava_aid)
					synced += 1
				except Exception:
					logging.exception("Error while importing an activity; skipping.")
			# next page
			page += 1
	except Exception as e:
		logging.exception("Failed to fetch athlete activities: %s", e)
		return {"synced": synced, "error": str(e)}

	return {"synced": synced}


# new helper: refresh a user's access token using their refresh_token
def refresh_user_token(user: User, db: Session) -> bool:
    """
    Try to refresh the Strava access token for the given user.
    Returns True if refreshed and DB updated, False otherwise.
    """
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")
    if not user.refresh_token or not client_id or not client_secret:
        logging.warning("Cannot refresh token: missing refresh_token or client credentials.")
        return False
    try:
        resp = requests.post("https://www.strava.com/oauth/token", data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": user.refresh_token
        }, timeout=10)
        resp.raise_for_status()
        tok = resp.json()
        new_access = tok.get("access_token")
        new_refresh = tok.get("refresh_token")
        if new_access:
            user.access_token = new_access
            if new_refresh:
                user.refresh_token = new_refresh
            try:
                db.add(user)
                db.commit()
                db.refresh(user)
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
            logging.info("Refreshed access token for user %s", user.id)
            return True
    except Exception:
        logging.exception("Failed to refresh token for user %s", getattr(user, "id", None))
    return False


@router.get("/login")
async def login(request: Request):
    """
    Browser-Aufruf -> Redirect zu Strava.
    XHR/Accept: application/json -> JSON mit auth_url.
    Bei fehlender/ungültiger Konfiguration wird eine erklärende HTML-Seite zurückgegeben.
    """
    invalid, msg = _invalid_client_config()
    if invalid:
        html = f"""
        <!doctype html><html><head><meta charset="utf-8"><title>Strava Login Fehler</title></head>
        <body style="font-family:Arial,sans-serif;padding:20px">
          <h2>Strava OAuth konfigurationsfehler</h2>
          <p>{msg}</p>
          <p>Bitte trage in deiner <code>.env</code> die richtigen Werte ein, z.B.<br>
             <code>STRAVA_CLIENT_ID=123456</code><br>
             <code>STRAVA_CLIENT_SECRET=your_secret_here</code>
          </p>
        </body></html>
        """
        return HTMLResponse(content=html, status_code=400)

    # build auth url using the incoming request (so ngrok/public host is used if present)
    auth_url = build_strava_auth_url(request)

    # If we couldn't build a valid redirect (empty auth_url), show explanatory page
    if not auth_url:
        html = f"""
        <!doctype html><html><head><meta charset="utf-8"><title>Strava Redirect Konfiguration</title></head>
        <body style="font-family:Arial,sans-serif;padding:20px">
          <h2>Ungültige STRAVA_REDIRECT_URI</h2>
          <p>Der Server kann keine gültige Redirect‑URL für Strava ermitteln.</p>
          <p>Prüfe die Umgebungsvariable <code>STRAVA_REDIRECT_URI</code> in Render — sie darf nicht auf <code>localhost</code> verweisen und muss auf:</p>
          <pre>https://november-challenge-1.onrender.com/auth/callback</pre>
          <p>Nach der Anpassung neu deployen.</p>
        </body></html>
        """
        return HTMLResponse(content=html, status_code=500)

    accept = (request.headers.get("accept") or "").lower()
    xreq = request.headers.get("x-requested-with") or ""
    if "application/json" in accept or xreq.lower() == "xmlhttprequest":
        return JSONResponse({"auth_url": auth_url})
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(code: str | None = None, state: str | None = None, db: Session = Depends(get_db)):
    """
    Demo-callback:
    - tauscht 'code' gegen Strava-Tokens
    - legt/aktualisiert User in der DB
    - gibt ein HTML zurück, das per postMessage das opener-window benachrichtigt und das Popup schließt.
    """
    if not code:
        payload = {"type": "strava_auth_complete", "success": False, "error": "no_code"}
        html = f"""
        <!doctype html>
        <html>
          <head><meta charset="utf-8" /></head>
          <body>
            <p>No code returned by Strava. This window will close.</p>
            <script>
              try {{
                window.opener && window.opener.postMessage({payload!r}, "*");
              }} catch(e){{}}
              setTimeout(()=>window.close(), 800);
            </script>
          </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=400)

    token_url = "https://www.strava.com/oauth/token"
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")
    try:
        resp = requests.post(token_url, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code"
        }, timeout=10)
        # handle non-200 explicitly to detect Strava messages (e.g. connected-athletes limit)
        if resp.status_code != 200:
            text = resp.text or ""
            # check for typical Strava "connected athletes" message fragments
            if "connected" in text.lower() and "athlete" in text.lower() or "limit" in text.lower():
                html = f"""
                <!doctype html><html><head><meta charset="utf-8"><title>Strava App Limit erreicht</title></head>
                <body style="font-family:Arial,sans-serif;padding:20px">
                  <h2>Strava: App‑Limit erreicht</h2>
                  <p>Strava hat gemeldet, dass die Anwendung das Limit verbundener Sportler überschritten hat.</p>
                  <p>Optionen:</p>
                  <ol>
                    <li>Kontaktiere Strava Developer Support und bitte um eine Kontingenterhöhung:
                        <a href="https://support.strava.com/hc/en-us/requests/new?ticket_form_id=360000051848" target="_blank">Strava Support</a>
                    </li>
                    <li>Erstelle vorübergehend eine eigene Strava‑App (Developer Dashboard) und trage deren Client-ID/Secret in deine <code>.env</code> ein, um Tests zu machen.</li>
                    <li>Teste manuell mit einer bekannten Activity‑ID (ohne OAuth) via: <code>/activities/process_by_strava/{'{activity_id}'}?owner_strava_id=YOUR_STRAVA_ID</code></li>
                  </ol>
                  <pre style="background:#f6f6f6;padding:10px;border-radius:4px">{text}</pre>
                </body></html>
                """
                return HTMLResponse(content=html, status_code=502)
            # otherwise raise to existing handler
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        payload = {"type": "strava_auth_complete", "success": False, "error": "token_exchange_failed", "details": str(e)}
        html = f"""
        <!doctype html>
        <html>
          <head><meta charset="utf-8" /></head>
          <body>
            <p>Token exchange failed. This window will close.</p>
            <pre>{str(e)}</pre>
            <script>
              try {{
                window.opener && window.opener.postMessage({payload!r}, "*");
              }} catch(e){{}}
              setTimeout(()=>window.close(), 1200);
            </script>
          </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=502)

    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    athlete = data.get("athlete") or {}
    strava_id = athlete.get("id")
    name_parts = []
    if athlete.get("firstname"):
        name_parts.append(athlete.get("firstname"))
    if athlete.get("lastname"):
        name_parts.append(athlete.get("lastname"))
    name = " ".join(name_parts) if name_parts else athlete.get("username") or "Strava User"

    if not strava_id or not access_token:
        payload = {"type": "strava_auth_complete", "success": False, "error": "invalid_token_response", "response": data}
        html = f"""
        <!doctype html>
        <html>
          <head><meta charset="utf-8" /></head>
          <body>
            <p>Invalid token response. This window will close.</p>
            <script>
              try {{
                window.opener && window.opener.postMessage({payload!r}, "*");
              }} catch(e){{}}
              setTimeout(()=>window.close(), 1200);
            </script>
          </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=502)

    # create or update user in DB
    try:
        user = db.query(User).filter_by(strava_id=strava_id).first()
        if not user:
            user = User(name=name, strava_id=strava_id, access_token=access_token, refresh_token=refresh_token)
            db.add(user)
        else:
            user.name = name
            user.access_token = access_token
            user.refresh_token = refresh_token
        # ensure slots default/length
        try:
            user.ensure_slots()
        except Exception:
            pass
        db.commit()
        db.refresh(user)
    except Exception as e:
        # rollback and log the full traceback so you can see the root cause on the server
        try:
            db.rollback()
        except Exception:
            pass
        logging.error("Database error during auth callback: %s\n%s", e, traceback.format_exc())
        payload = {
            "type": "strava_auth_complete",
            "success": False,
            "error": "db_error",
            "details": str(e),
            "hint": "Check DATABASE_URL and that the DB is reachable. See server logs for full traceback."
        }
        html = f"""
        <!doctype html>
        <html>
          <head><meta charset="utf-8" /></head>
          <body>
            <h3>Database error during authentication</h3>
            <pre>{str(e)}</pre>
            <p>Please check your DATABASE_URL in <code>.env</code> and the server logs for details.</p>
            <script>
              try {{
                window.opener && window.opener.postMessage({payload!r}, "*");
              }} catch(e){{}}
              setTimeout(()=>window.close(), 2000);
            </script>
          </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=500)

    # After successful user creation/update: sync recent activities from Strava automatically
    try:
        sync_result = sync_recent_activities_from_strava(user, db)
        logging.info("Sync result after auth: %s", sync_result)
    except Exception:
        logging.exception("Automatic sync after registration failed.")

    # success -> inform opener with basic user info
    payload = {"type": "strava_auth_complete", "success": True, "user": {"id": user.id, "name": user.name, "strava_id": user.strava_id}}
    html = f"""
    <!doctype html>
    <html>
      <head><meta charset="utf-8" /></head>
      <body>
        <p>Authentication complete. This window will close.</p>
        <script>
          try {{
            window.opener && window.opener.postMessage({payload!r}, "*");
          }} catch(e){{}}
          setTimeout(()=>window.close(), 800);
        </script>
      </body>
    </html>
    """
    return HTMLResponse(content=html)


# New debug endpoint to inspect runtime config (masked)
@router.get("/debug/config")
async def debug_auth_config(request: Request, db = Depends(get_db)):
    """
    Returns masked values for STRAVA_REDIRECT_URI and DATABASE_URL as seen by the running process.
    Use this after deploy to verify the service actually has the correct env configured.
    """
    def _mask_url(u: str) -> str:
        if not u:
            return "(not set)"
        try:
            # simple mask for credentials in URLs like postgres://user:pass@host:port/db
            if "@" in u and ":" in u.split("@")[0]:
                userinfo, hostinfo = u.split("@", 1)
                user = userinfo.split(":", 1)[0]
                return f"{user}:***@{hostinfo}"
        except Exception:
            pass
        return u if len(u) < 80 else u[:50] + "..." 

    env_redirect = os.getenv("STRAVA_REDIRECT_URI", "")
    if env_redirect.strip() and not env_redirect.strip().lower().startswith((
        "http://localhost", "https://localhost", "http://127.0.0.1", "https://127.0.0.1"
    )):
        used_redirect = env_redirect
    else:
        used_redirect = str(request.base_url).rstrip("/") + "/auth/callback"

    return {
        "used_redirect_uri": used_redirect,
        "env_STRAVA_REDIRECT_URI_masked": _mask_url(env_redirect),
        "STRAVA_CLIENT_ID_set": bool(os.getenv("STRAVA_CLIENT_ID")),
        "DATABASE_URL_masked": _mask_url(os.getenv("DATABASE_URL", "")),
        "notes": "If used_redirect_uri contains localhost, set STRAVA_REDIRECT_URI to your Render domain in the service env vars."
    }
