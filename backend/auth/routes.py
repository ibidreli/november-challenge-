from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from dotenv import load_dotenv
import os
from urllib.parse import urlencode

# added imports
import requests
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
import logging
import traceback

load_dotenv()

router = APIRouter()


def build_strava_auth_url():
    client_id = os.getenv("STRAVA_CLIENT_ID")
    redirect_uri = os.getenv("STRAVA_REDIRECT_URI") or "http://localhost:8000/auth/callback"
    scope = os.getenv("STRAVA_SCOPE", "read,activity:read_all")
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "approval_prompt": "auto",
        "scope": scope,
    }
    return "https://www.strava.com/oauth/authorize?" + urlencode(params)


def _invalid_client_config():
    cid = os.getenv("STRAVA_CLIENT_ID")
    csec = os.getenv("STRAVA_CLIENT_SECRET")
    if not cid or cid.strip() == "" or cid.strip().startswith("<") or not cid.isdigit():
        return True, "STRAVA_CLIENT_ID fehlt oder ist ungültig (muss eine Zahl ohne spitze Klammern sein)."
    if not csec or csec.strip() == "" or csec.strip().startswith("<"):
        return True, "STRAVA_CLIENT_SECRET fehlt oder ist offensichtlich nicht gesetzt."
    return False, None


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

    auth_url = build_strava_auth_url()
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
