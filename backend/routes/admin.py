"""
Admin routes for managing users and activities.
Requires admin authentication via password/token.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from models.user import User
from models.activity import Activity
from models.claim import Claim
from database import get_db
from typing import Optional
import os
import datetime
import secrets
import hashlib

router = APIRouter()

# Admin config from environment
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_TOKENS = {}  # Store valid tokens with expiry


def hash_password(password: str) -> str:
    """Hash password for storage/comparison"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_token() -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)


def verify_admin_token(token: Optional[str] = Header(None, alias="X-Admin-Token")) -> str:
    """Dependency to verify admin token"""
    if not token:
        raise HTTPException(status_code=401, detail="Admin token required")
    
    # Check if token is valid and not expired
    if token not in ADMIN_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid or expired admin token")
    
    token_data = ADMIN_TOKENS[token]
    if datetime.datetime.now() > token_data["expires_at"]:
        del ADMIN_TOKENS[token]
        raise HTTPException(status_code=401, detail="Token expired")
    
    # Refresh expiry time on each request
    token_data["expires_at"] = datetime.datetime.now() + datetime.timedelta(hours=2)
    return token


@router.post("/login")
def admin_login(password: str, db: Session = Depends(get_db)):
    """
    Admin login with password.
    Returns: {"token": "...", "expires_in": 7200}
    """
    if hash_password(password) != hash_password(ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Generate new token
    token = generate_token()
    ADMIN_TOKENS[token] = {
        "expires_at": datetime.datetime.now() + datetime.timedelta(hours=2)
    }
    
    return {
        "token": token,
        "expires_in": 7200  # 2 hours in seconds
    }


@router.post("/logout")
def admin_logout(token: str = Depends(verify_admin_token)):
    """Logout: invalidate token"""
    if token in ADMIN_TOKENS:
        del ADMIN_TOKENS[token]
    return {"status": "logged_out"}


# ============ USER MANAGEMENT ============

@router.get("/users")
def get_all_users_admin(db: Session = Depends(get_db), token: str = Depends(verify_admin_token)):
    """Get all users for admin management"""
    users = db.query(User).all()
    result = []
    for u in users:
        try:
            u.ensure_slots()
        except Exception:
            pass
        result.append({
            "id": u.id,
            "name": u.name,
            "strava_id": u.strava_id,
            "total_score": int(u.total_score or 0),
            "slots": u.slots
        })
    return result


@router.post("/users")
def create_user_admin(name: str, db: Session = Depends(get_db), token: str = Depends(verify_admin_token)):
    """Create a new user"""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    
    # Check if user already exists
    existing = db.query(User).filter(User.name == name.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this name already exists")
    
    user = User(name=name.strip(), slots=[None] * 30)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "name": user.name,
        "total_score": 0,
        "slots": user.slots
    }


@router.put("/users/{user_id}")
def update_user_admin(
    user_id: int,
    name: Optional[str] = None,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """Update user information"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if name and name.strip():
        user.name = name.strip()
    
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "name": user.name,
        "total_score": int(user.total_score or 0),
        "slots": user.slots
    }


@router.delete("/users/{user_id}")
def delete_user_admin(user_id: int, db: Session = Depends(get_db), token: str = Depends(verify_admin_token)):
    """Delete a user and all associated activities/claims"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete associated claims and activities
    db.query(Claim).filter(Claim.user_id == user_id).delete()
    db.query(Activity).filter(Activity.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    
    return {"status": "deleted"}


# ============ ACTIVITY MANAGEMENT ============

@router.get("/users/{user_id}/activities")
def get_user_activities_admin(
    user_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """Get all activities for a user (both manual and Strava)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    activities = db.query(Activity).filter(Activity.user_id == user_id).all()
    result = []
    for act in activities:
        result.append({
            "id": act.id,
            "date": act.date.isoformat() if act.date else None,
            "distance_km": float(act.distance_km or 0),
            "effective_km": act.effective_km,
            "status": act.status,
            "is_manual": bool(act.is_manual),
            "strava_id": act.strava_id
        })
    
    return sorted(result, key=lambda x: x["date"] or "", reverse=True)


@router.post("/users/{user_id}/activities")
def create_activity_admin(
    user_id: int,
    date: str,  # ISO format: "2024-11-15"
    distance_km: float,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """
    Create a manual activity for a user.
    Manual activities have priority and won't be overwritten by Strava sync.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if distance_km < 0:
        raise HTTPException(status_code=400, detail="Distance must be positive")
    
    try:
        activity_date = datetime.datetime.fromisoformat(date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use ISO format (YYYY-MM-DD)")
    
    # Check if activity already exists for this user/date (manual)
    existing = db.query(Activity).filter(
        Activity.user_id == user_id,
        Activity.date == activity_date,
        Activity.is_manual == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Manual activity already exists for this date")
    
    # Create new manual activity
    activity = Activity(
        user_id=user_id,
        date=activity_date,
        distance_km=distance_km,
        status="pending",
        is_manual=True,
        strava_id=None  # Manual activities don't have strava_id
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    
    return {
        "id": activity.id,
        "date": activity.date.isoformat(),
        "distance_km": float(activity.distance_km),
        "status": activity.status,
        "is_manual": True
    }


@router.put("/users/{user_id}/activities/{activity_id}")
def update_activity_admin(
    user_id: int,
    activity_id: int,
    distance_km: Optional[float] = None,
    date: Optional[str] = None,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """Update a manual activity"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == user_id
    ).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    if not activity.is_manual:
        raise HTTPException(status_code=400, detail="Cannot edit Strava activities")
    
    if distance_km is not None:
        if distance_km < 0:
            raise HTTPException(status_code=400, detail="Distance must be positive")
        activity.distance_km = distance_km
    
    if date is not None:
        try:
            activity.date = datetime.datetime.fromisoformat(date).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    db.commit()
    db.refresh(activity)
    
    return {
        "id": activity.id,
        "date": activity.date.isoformat(),
        "distance_km": float(activity.distance_km),
        "status": activity.status,
        "is_manual": True
    }


@router.delete("/users/{user_id}/activities/{activity_id}")
def delete_activity_admin(
    user_id: int,
    activity_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """Delete an activity and associated claim"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == user_id
    ).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    # Delete associated claim if exists
    claim = db.query(Claim).filter(Claim.activity_id == activity_id).first()
    if claim:
        # Undo score changes
        if user.total_score and claim.km:
            user.total_score = max(0, (user.total_score or 0) - claim.km)
        
        # FIX: slots sind integers, nicht dicts mit activity_id
        if user.slots and isinstance(user.slots, list):
            for i, slot in enumerate(user.slots):
                # Wenn slot dem km der Claim entspricht, setze auf None
                if slot == claim.km:
                    user.slots[i] = None
                    break
        
        db.delete(claim)
    
    db.delete(activity)
    db.commit()
    
    return {"status": "deleted"}


@router.post("/users/{user_id}/reset-slots")
def reset_user_slots(
    user_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """Reset all slots and score for a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Reset slots and score
    user.slots = [None] * 30
    user.total_score = 0
    
    # Delete all claims
    db.query(Claim).filter(Claim.user_id == user_id).delete()
    
    # Reset all activities to pending
    activities = db.query(Activity).filter(Activity.user_id == user_id).all()
    for act in activities:
        act.status = "pending"
        act.effective_km = None
    
    db.commit()
    
    return {"status": "reset"}
