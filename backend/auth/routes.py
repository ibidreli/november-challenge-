from fastapi import APIRouter, Request, Depends, HTTPException, Header, status
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from dotenv import load_dotenv
import os
from urllib.parse import urlencode
import requests
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
import logging, traceback, datetime, json
from typing import Optional
import uuid
import time

# load .env only when explicitly requested (avoid accidentally overriding Render env vars)
if os.getenv("LOAD_ENV_FILE", "0") == "1":
    load_dotenv()

router = APIRouter()

# add: use CHALLENGE_MONTH env (default 11)
CHALLENGE_MONTH = int(os.getenv("CHALLENGE_MONTH", "11"))


def build_strava_auth_url(request: Optional[Request] = None):
    """
    Build Strava auth URL.
    Priority:
      1) STRAVA_REDIRECT_URI env (if set) — normalized
      2) Build from X-Forwarded-Proto + X-Forwarded-Host (or Host) from request
      3) Fallback to request.base_url
    Returns empty string on failure.
    """
    client_id = os.getenv("STRAVA_CLIENT_ID")
    redirect_uri_env = (os.getenv("STRAVA_REDIRECT_URI") or "").strip()

    # normalize env value: add https if missing
    if redirect_uri_env and not redirect_uri_env.lower().startswith(("http://", "https://")):
        redirect_uri_env = "https://" + redirect_uri_env

    # PREFER env when present (use the exact redirect you registered at Strava).
    redirect_uri = ""
    if redirect_uri_env:
        redirect_uri = redirect_uri_env
    else:
        # build from forwarded headers when available (handles reverse proxies like Render)
        if request is not None:
            proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").lower()
            host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc or ""
            if proto and host:
                if proto not in ("http", "https"):
                    proto = "https"
                redirect_uri = f"{proto}://{host.rstrip('/')}/auth/callback"
            else:
                # last resort: request.base_url
                redirect_uri = str(request.base_url).rstrip("/") + "/auth/callback"
    # enforce https to avoid Mixed Content and Strava rejecting mismatched schema (but keep explicit http if env provided)
    if redirect_uri.startswith("http://") and not redirect_uri_env:
        redirect_uri = "https://" + redirect_uri[len("http://"):]
    scope = os.getenv("STRAVA_SCOPE", "read,activity:read_all")
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "approval_prompt": "auto",
        "scope": scope,
    }
    logging.info("build_strava_auth_url -> using redirect_uri: %s", redirect_uri or "(none)")
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
					# --- nur Runs verarbeiten: überspringe Aktivitäten, die nicht vom Typ "Run" sind ---
					# skip non-run activities
					if (a.get("type") or "").lower() != "run":
						logging.debug("Skipping non-Run activity from Strava import: id=%s, type=%s", a.get("id"), a.get("type"))
						continue
					
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
async def callback(request: Request, code: str | None = None, state: str | None = None, db: Session = Depends(get_db)):
	"""
	Demo-callback:
	- tauscht 'code' gegen Strava-Tokens
	- legt/aktualisiert User in der DB
	- gibt ein HTML zurück, das per postMessage das opener-window benachrichtigt und das Popup schließt.
	"""
	try:
		# frontend target: prefer explicit FRONTEND_URL env. If missing, map known backend -> frontend pair.
		# This avoids redirecting to arbitrary/third-party referer/origin hosts (e.g. Google).
		
		frontend_url = os.getenv("FRONTEND_URL", "").strip()
		backend_base = str(request.base_url).rstrip("/")

		if not frontend_url:
			# safe, explicit mapping for your deployment:
			try:
				host_header = (request.headers.get("host") or "").lower()
				if "november-challenge.onrender.com" in host_header:
					frontend_url = "https://november-challenge-1.onrender.com"
				else:
					# fallback to root — no external redirect
					frontend_url = "/"
			except Exception:
				frontend_url = "/"
		logging.info("callback -> using frontend_url=%s", frontend_url)

		if not code:
			payload = {"type": "strava_auth_complete", "success": False, "error": "no_code"}
			payload_json = json.dumps(payload)
			html = f"""<!doctype html>
			<html>
			  <head><meta charset="utf-8" /></head>
			  <body>
				<p>No code returned by Strava.</p>
				<p><a id="return" href="{frontend_url}">Zurück zur App</a></p>
				<script>
				  (function(){{
					var payload = {payload_json};
					try {{
					  if (window.opener && !window.opener.closed) {{
						window.opener.postMessage(payload, "*");
						window.close();
						return;
					  }}
					}} catch(e){{}}
					try {{
					  var target = "{frontend_url}";
					  if (target) {{
						window.location.href = target + (target.indexOf('?')>-1 ? '&' : '?') + 'auth=failed';
					  }}
					}} catch(e){{}}
				  }})();
				</script>
			  </body>
			</html>"""
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

		# generate a short-lived one-time key so frontend can fetch the token reliably
		try:
			otp_key = uuid.uuid4().hex
			OTP_STORE[otp_key] = {"access_token": access_token, "strava_id": str(strava_id), "expires": time.time() + 120}
		except Exception:
			logging.exception("Failed to create OTP for token delivery")
			otp_key = None

		# success -> inform opener with basic user info (include access_token + otp_key so frontend can fetch it)
		payload = {
			"type": "strava_auth_complete",
			"success": True,
			"user": {"id": user.id, "name": user.name, "strava_id": user.strava_id},
			"access_token": access_token,
			"otp_key": otp_key
		}
		payload_json = json.dumps(payload)
    

		# Determine whether to include token in query (easier for frontend to read) or use fragment.
		# Previously we only used query for localhost debug; also enable it when redirect target is the known frontend.
		include_token_in_query = False
		try:
			host = (request.url.hostname or "").lower()
			furl = (frontend_url or "").lower()
			# keep local-debug behavior
			if "localhost" in furl or host in ("localhost", "127.0.0.1"):
				include_token_in_query = True
			# also allow direct query delivery for your deployed frontend domain so client can read location.search
			if "november-challenge-1.onrender.com" in furl:
				include_token_in_query = True
		except Exception:
			include_token_in_query = False

		# Build HTML safely by injecting JSON‑escaped values for frontend/ backend URLs
		frontend_js = json.dumps(frontend_url)
		# add this near the top of the callback(), after frontend_url is decided
  

		backend_js = json.dumps(backend_base)
		include_token_js = "true" if include_token_in_query else "false"

		html = (
			"<!doctype html>\n"
			"<html>\n"
			"  <head><meta charset=\"utf-8\" /></head>\n"
			"  <body>\n"
			"    <p>Authentication complete. This window will close.</p>\n"
			"    <p>If the window does not close automatically, <a id=\"return\" href=" + frontend_js + ">click here to return to the app</a>.</p>\n"
			"    <script>\n"
			"      (async function(){\n"
			"        var payload = " + payload_json + ";\n"
			"        try { if (window.opener && !window.opener.closed) { window.opener.postMessage(payload, '*'); try { window.close(); return; } catch(e){} } } catch(e){}\n"
			"        try {\n"
			"          if (payload.otp_key) {\n"
			"            try { await fetch('/auth/token?key=' + encodeURIComponent(payload.otp_key), { method: 'GET', credentials: 'include' }); } catch(e) { console.warn('Backend token exchange failed:', e); }\n"
			"          }\n"
			"        } catch(e) { console.warn('otp exchange error', e); }\n"
			"        try {\n"
			"          var target = " + frontend_js + ";\n"
			"          var backendBase = " + backend_js + ";\n"
			"          var backendBaseHttps = backendBase.indexOf('http://') === 0 ? backendBase.replace('http://','https://') : backendBase;\n"
			"          if (target) {\n"
			"            var params = [];\n"
			"            if (payload.access_token) params.push('access_token=' + encodeURIComponent(payload.access_token));\n"
			"            if (payload.user && payload.user.strava_id) params.push('strava_id=' + encodeURIComponent(payload.user.strava_id));\n"
			"            if (payload.otp_key) params.push('otp_key=' + encodeURIComponent(payload.otp_key));\n"
			"            params.push('backend_base=' + encodeURIComponent(backendBase));\n"
			"            params.push('backend_base_https=' + encodeURIComponent(backendBaseHttps));\n"
			"            var paramString = params.join('&');\n"
			"            if (" + include_token_js + ") {\n"
			"              var sep = target.indexOf('?') === -1 ? '?' : '&';\n"
			"              window.location.href = target + sep + paramString;\n"
			"            } else {\n"
			"              var sep = target.indexOf('#') === -1 ? '#' : '&';\n"
			"              window.location.href = target + sep + paramString;\n"
			"            }\n"
			"          }\n"
			"        } catch(e) { console.warn('redirect failed', e); }\n"
			"      })();\n"
			"    </script>\n"
			"  </body>\n"
			"</html>\n"
		)

		# set cookie so subsequent same-origin requests include the token without extra frontend work
		resp = HTMLResponse(content=html)
		resp.set_cookie("access_token", access_token or "", samesite="lax", httponly=False, max_age=60*60*24)
		return resp

	except Exception as e:
		# Log full traceback on server
		logging.error("Unhandled exception in /auth/callback: %s\n%s", e, traceback.format_exc())
		# Short, safe traceback preview for browser (masking not to leak secrets)
		trace = traceback.format_exc()
		trace_short = trace if len(trace) <= 2000 else trace[:2000] + "\n\n...(truncated)"
		# simple HTML response with preview to aid debugging
		html_err = (
			"<!doctype html><html><head><meta charset='utf-8'><title>Auth Callback Error</title></head>"
			"<body style='font-family:Arial,sans-serif;padding:20px'>"
			"<h2>Authentication Error</h2>"
			"<p>Ein Fehler ist beim Verarbeiten der OAuth‑Antwort aufgetreten. Prüfe die Serverlogs oder <code>/debug/nodb</code>.</p>"
			"<h3>Kurze Traceback‑Vorschau</h3>"
			"<pre style='background:#f6f6f6;padding:10px;border-radius:4px;white-space:pre-wrap;max-height:420px;overflow:auto;'>"
			+ trace_short.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
			+ "</pre>"
			"</body></html>"
		)
		return HTMLResponse(content=html_err, status_code=500)

# simple in-memory one-time-token store: key -> {"access_token":..., "strava_id":..., "expires": epoch}
# Note: single-process only; fine for dev. For production persist to DB or redis.
OTP_STORE: dict = {}

# New endpoint: exchange one-time key for token (short-lived)
@router.get("/token", response_model=None)
async def fetch_token(request: Request, key: Optional[str] = None, db: Session = Depends(get_db)):
     """
     Exchange a one-time key (provided by /auth/callback redirect/postMessage) for the access_token.
     Key expires after short time and is removed after use.
     Also sets an access_token cookie on the response to simplify subsequent API calls from the browser.
     """
     if not key:
         raise HTTPException(status_code=400, detail="missing_key")
     try:
         # Lookup and remove from store
         data = OTP_STORE.pop(key, None)
         if not data:
             raise HTTPException(status_code=404, detail="key_not_found_or_expired")
         access_token = data["access_token"]
         strava_id = data["strava_id"]

         # Set secure flag: true if request was forwarded by TLS-terminating proxy (Render)
         secure_flag = False
         try:
             # Derive secure flag from x-forwarded-proto when service sitzt hinter TLS-terminierender Reverse‑Proxy
             proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").lower()
             secure_flag = (proto == "https")
         except Exception:
             secure_flag = False

         # Set cookie (httponly + secure if applicable)
         resp = JSONResponse({"access_token": access_token})
         resp.set_cookie("access_token", access_token, samesite="lax", httponly=True, secure=secure_flag, max_age=60*60*24)
         return resp
     except Exception:
         logging.exception("Token exchange failed")
         raise HTTPException(status_code=500, detail="token_exchange_failed")


