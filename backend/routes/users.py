from fastapi import APIRouter, Depends, Query, Header, HTTPException, Request
from sqlalchemy.orm import Session
from models.user import User
from database import get_db
from typing import Optional


router = APIRouter()


@router.get("/me")
def get_current_user(sync: bool = Query(False), request: Request = None, auth_header: Optional[str] = Header(None, alias="Authorization"), db: Session = Depends(get_db)):
    """
    Require Authorization: Bearer <access_token> or access_token cookie.
    If no valid token provided, return 401 so frontend shows login screen.
    """
    # extract bearer token from header first, otherwise from cookie
    token = None
    if auth_header:
        t = auth_header.strip()
        if t.lower().startswith("bearer "):
            t = t[7:].strip()
        if t:
            token = t
    if not token and request is not None:
        # cookie fallback
        token = request.cookies.get("access_token") or None
    # query param fallback (used in local-debug redirect)
    if not token and request is not None:
        qp = request.query_params.get("access_token")
        if qp:
            token = qp

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter_by(access_token=token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # optionally sync only this user (useful for frontend to refresh current user's activities)
    if sync:
        try:
            # import locally to avoid circular import at module import time
            from auth.routes import sync_recent_activities_from_strava
            sync_result = sync_recent_activities_from_strava(user, db)
            # ignore/surface result as needed
        except Exception:
            pass
    user.ensure_slots()
    return {
        "id": user.id,
        "name": user.name,
        "strava_id": user.strava_id,
        "total_score": user.total_score,
        "slots": user.slots
    }


@router.post("/sync_all")
def sync_all_users(db: Session = Depends(get_db)):
    """
    Trigger sync for all users (fetch activities from Strava since CHALLENGE_MONTH start).
    Frontend can call this on page load to ensure newest activities appear without re-auth.
    """
    users = db.query(User).all()
    summary = []
    try:
        from auth.routes import sync_recent_activities_from_strava
    except Exception:
        from backend.auth.routes import sync_recent_activities_from_strava

    for u in users:
        try:
            res = sync_recent_activities_from_strava(u, db)
            summary.append({"user_id": u.id, "strava_id": u.strava_id, "result": res})
        except Exception as e:
            summary.append({"user_id": u.id, "strava_id": u.strava_id, "error": str(e)})
    return {"synced": len(summary), "details": summary}


@router.get("/debug_sync/{user_id}")
def debug_sync_user(user_id: int, db: Session = Depends(get_db)):
    """
    Debug endpoint: Trigger sync for specific user and return detailed results.
    Shows what activities were synced, what was filtered, errors, etc.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return {"error": "user_not_found", "user_id": user_id}
    
    debug_info = {
        "user_id": user.id,
        "user_name": user.name,
        "strava_id": user.strava_id,
        "has_access_token": bool(user.access_token),
        "has_refresh_token": bool(user.refresh_token),
        "access_token_preview": user.access_token[:20] if user.access_token else None,
        "refresh_token_preview": user.refresh_token[:20] if user.refresh_token else None,
    }
    
    try:
        from auth.routes import sync_recent_activities_from_strava
    except Exception:
        from backend.auth.routes import sync_recent_activities_from_strava

    try:
        result = sync_recent_activities_from_strava(user, db)
        debug_info["sync_result"] = result
    except Exception as e:
        debug_info["sync_error"] = str(e)
        import traceback
        debug_info["sync_traceback"] = traceback.format_exc()

    # Also show current activities in DB for this user
    from models.activity import Activity
    activities = db.query(Activity).filter_by(user_id=user.id).all()
    debug_info["db_activities_count"] = len(activities)
    debug_info["db_activities"] = [
        {
            "id": a.id,
            "strava_id": a.strava_id,
            "date": str(a.date) if a.date else None,
            "distance_km": a.distance_km,
            "status": a.status,
            "is_manual": a.is_manual,
            "effective_km": a.effective_km,
        }
        for a in activities
    ]

    return debug_info


@router.get("/debug_token_test/{user_id}")
def debug_token_test(user_id: int, db: Session = Depends(get_db)):
    """
    Debug endpoint: Test if the user's access token is valid by calling Strava API directly.
    Also fetch recent activities to see what Strava has for this athlete.
    Returns athlete info if token is valid, or error if not.
    """
    import requests
    import datetime
    
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return {"error": "user_not_found", "user_id": user_id}
    
    debug_info = {
        "user_id": user.id,
        "user_name": user.name,
        "strava_id": user.strava_id,
    }
    
    # First, try to refresh the token
    try:
        from auth.routes import refresh_user_token
        refresh_result = refresh_user_token(user, db)
        debug_info["token_refresh_result"] = "success" if refresh_result else "failed"
    except Exception as e:
        debug_info["token_refresh_error"] = str(e)
    
    # Now test the token by calling Strava API
    if not user.access_token:
        debug_info["token_test_result"] = "no_access_token"
        return debug_info
    
    try:
        headers = {"Authorization": f"Bearer {user.access_token}"}
        # Try to get athlete info (simple test that doesn't count against rate limits much)
        r = requests.get("https://www.strava.com/api/v3/athlete", headers=headers, timeout=10)
        
        debug_info["strava_api_status"] = r.status_code
        debug_info["strava_api_response"] = r.text[:500]  # First 500 chars
        
        if r.status_code == 200:
            athlete = r.json()
            debug_info["athlete_name"] = athlete.get("firstname", "") + " " + athlete.get("lastname", "")
            debug_info["token_test_result"] = "valid"
        elif r.status_code == 401:
            debug_info["token_test_result"] = "unauthorized - token is invalid or expired"
        else:
            debug_info["token_test_result"] = f"error_{r.status_code}"
    except Exception as e:
        debug_info["token_test_error"] = str(e)
        debug_info["token_test_result"] = "request_failed"
    
    # Now fetch recent activities from Strava directly
    if user.access_token:
        try:
            headers = {"Authorization": f"Bearer {user.access_token}"}
            # Fetch activities after Nov 1, 2025
            nov_1_2025 = datetime.datetime(2025, 11, 1, 0, 0, 0)
            since_epoch = int(nov_1_2025.timestamp())
            
            params = {
                "after": since_epoch,
                "per_page": 50,
                "page": 1
            }
            r = requests.get("https://www.strava.com/api/v3/athlete/activities", headers=headers, params=params, timeout=10)
            
            if r.status_code == 200:
                activities = r.json() or []
                debug_info["strava_recent_activities_count"] = len(activities)
                debug_info["strava_recent_activities"] = [
                    {
                        "id": a.get("id"),
                        "name": a.get("name"),
                        "type": a.get("type"),
                        "distance_m": a.get("distance"),
                        "distance_km": (a.get("distance") or 0) / 1000.0,
                        "start_date_local": a.get("start_date_local"),
                    }
                    for a in activities[:10]  # First 10
                ]
            else:
                debug_info["strava_activities_error"] = f"Status {r.status_code}: {r.text[:200]}"
        except Exception as e:
            debug_info["strava_activities_error"] = str(e)
    
    return debug_info


@router.get("/debug_strava_all/{user_id}")
def debug_strava_all(user_id: int, db: Session = Depends(get_db)):
    """
    Debug endpoint: Fetch ALL recent activities from Strava (no time filter).
    This shows everything Robert has without the 'after' timestamp filter.
    """
    import requests
    
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return {"error": "user_not_found", "user_id": user_id}
    
    if not user.access_token:
        return {"error": "no_access_token"}
    
    debug_info = {
        "user_id": user.id,
        "user_name": user.name,
        "strava_id": user.strava_id,
    }
    
    try:
        headers = {"Authorization": f"Bearer {user.access_token}"}
        # Get ALL recent activities (NO time filter, just most recent 50)
        params = {
            "per_page": 50,
            "page": 1
        }
        r = requests.get("https://www.strava.com/api/v3/athlete/activities", headers=headers, params=params, timeout=10)
        
        if r.status_code == 200:
            activities = r.json() or []
            debug_info["total_activities_returned"] = len(activities)
            debug_info["activities"] = [
                {
                    "strava_id": a.get("id"),
                    "name": a.get("name"),
                    "type": a.get("type"),
                    "distance_km": round((a.get("distance") or 0) / 1000.0, 2),
                    "start_date_local": a.get("start_date_local"),
                    "start_date": a.get("start_date"),
                }
                for a in activities[:15]  # Show first 15
            ]
        else:
            debug_info["error"] = f"Strava API error: {r.status_code}"
            debug_info["response"] = r.text[:300]
    except Exception as e:
        debug_info["error"] = str(e)
        import traceback
        debug_info["traceback"] = traceback.format_exc()
    
    return debug_info


# New: simple listing endpoint for leaderboard
@router.get("/debug_raw")
def debug_raw_users(db: Session = Depends(get_db)):
    """
    Debug endpoint: returns raw user rows for inspection by frontend/dev.
    """
    try:
        users = db.query(User).all()
        out = []
        for u in users:
            try:
                u.ensure_slots()
            except Exception:
                pass
            out.append({
                "id": u.id,
                "name": u.name,
                "strava_id": u.strava_id,
                "total_score": int(u.total_score or 0),
                "slots": u.slots,
                "has_access_token": bool(u.access_token),
                "has_refresh_token": bool(u.refresh_token),
            })
        return out
    except Exception as e:
        return {"error": "db_error", "details": str(e)}


@router.get("/debug_all_activities")
def debug_all_activities(db: Session = Depends(get_db)):
    """
    Debug endpoint: Show ALL activities in database grouped by user.
    """
    try:
        from models.activity import Activity
        activities = db.query(Activity).all()
        
        # Group by user
        by_user = {}
        for a in activities:
            user_id = a.user_id
            if user_id not in by_user:
                by_user[user_id] = []
            by_user[user_id].append({
                "id": a.id,
                "strava_id": a.strava_id,
                "date": str(a.date) if a.date else None,
                "distance_km": float(a.distance_km) if a.distance_km else None,
                "status": a.status,
                "is_manual": a.is_manual,
                "effective_km": a.effective_km,
            })
        
        return {
            "total_activities": len(activities),
            "activities_by_user": by_user
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


@router.get("/")
def list_users(db: Session = Depends(get_db)):
    try:
        users = db.query(User).all()
        out = []
        for u in users:
            try:
                u.ensure_slots()
            except Exception:
                pass
            km_total = 0
            slots_out = []
            for s in (u.slots or []):
                # normalize slot representation: either null or integer km
                if isinstance(s, dict) and "km" in s and isinstance(s["km"], (int, float)):
                    km_val = int(s["km"])
                    km_total += km_val
                    slots_out.append(km_val)
                else:
                    slots_out.append(None)
            out.append({
                "id": u.id,
                "name": u.name,
                "total_score": int(u.total_score or 0),
                "km_total": km_total,
                "slots": slots_out
            })
        # sort by score desc, fallback to km_total
        out.sort(key=lambda x: (int(x.get("total_score", 0)), int(x.get("km_total", 0))), reverse=True)
        return out
    except Exception as e:
        # return an informative response instead of failing silently in frontend
        return {"error": "list_users_failed", "details": str(e)}