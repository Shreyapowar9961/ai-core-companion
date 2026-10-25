from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi.security import HTTPAuthorizationCredentials

from app.core.database import get_db
from app.core.security import (
    get_current_user, AuthUser, UserRole, create_access_token,
    verify_password, security_scheme
)
from app.core.config import settings
from app.core.audit import log_audit_event
from app.models.user import UserProfile, RevokedToken

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    facility_id: Optional[str] = None
    patient_id: Optional[str] = None

@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate clinician or administrator using Supabase Auth or database credentials.
    Roles are strictly retrieved from trusted database records (DB-05).
    """
    email_clean = req.email.strip().lower()

    # 1. Lookup user profile in database
    user_record = db.execute(
        select(UserProfile).where(UserProfile.email == email_clean)
    ).scalars().first()

    if not user_record:
        log_audit_event(
            db=db,
            event_type="AUTH_LOGIN_FAILED",
            actor_id=email_clean,
            actor_role="UNKNOWN",
            resource="auth",
            details={"reason": "User not found in clinical directory", "email": email_clean}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user_record.is_active:
        log_audit_event(
            db=db,
            event_type="AUTH_LOGIN_BLOCKED",
            actor_id=user_record.id,
            actor_role=user_record.role,
            resource="auth",
            details={"reason": "User account deactivated", "email": email_clean}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact hospital system administrator."
        )

    # 2. Authenticate credentials
    auth_success = False

    # A. Check Supabase GoTrue Auth if online, configured, and local auth not explicitly forced
    if not settings.LOCAL_AUTH_ENABLED and settings.SUPABASE_URL and not settings.SUPABASE_URL.startswith("https://your-project") and settings.SUPABASE_ANON_KEY and not settings.SUPABASE_ANON_KEY.startswith("your-anon"):
        try:
            import urllib.request
            import json
            req_body = json.dumps({"email": email_clean, "password": req.password}).encode("utf-8")
            sb_req = urllib.request.Request(
                f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
                data=req_body,
                headers={"Content-Type": "application/json", "apikey": settings.SUPABASE_ANON_KEY}
            )
            with urllib.request.urlopen(sb_req, timeout=5) as resp:
                if resp.status == 200:
                    auth_success = True
        except Exception:
            # Fall back to database password verification
            pass

    # B. Local database password verification (for development, testing, and seeded clinicians)
    if not auth_success and user_record.password_hash:
        if verify_password(req.password, user_record.password_hash):
            auth_success = True

    if not auth_success:
        log_audit_event(
            db=db,
            event_type="AUTH_LOGIN_FAILED",
            actor_id=user_record.id,
            actor_role=user_record.role,
            resource="auth",
            details={"reason": "Incorrect password", "email": email_clean}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # 3. Issue signed JWT with trusted role from database
    token_payload = {
        "sub": user_record.id,
        "email": user_record.email,
        "role": user_record.role,
        "facility_id": user_record.facility_id,
        "name": user_record.full_name
    }
    access_token = create_access_token(token_payload)

    log_audit_event(
        db=db,
        event_type="AUTH_LOGIN_SUCCESS",
        actor_id=user_record.id,
        actor_role=user_record.role,
        resource="auth",
        details={"facility_id": user_record.facility_id, "role": user_record.role}
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user_record.id,
            "email": user_record.email,
            "name": user_record.full_name,
            "role": user_record.role,
            "facility_id": user_record.facility_id
        }
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: AuthUser = Depends(get_current_user)):
    """
    Returns trusted authenticated staff context and RBAC role (DB-05).
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role.value,
        facility_id=current_user.facility_id,
        patient_id=current_user.patient_id
    )

@router.post("/logout")
def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Invalidates current session by blacklisting the active token signature.
    """
    if credentials and credentials.credentials:
        token = credentials.credentials.strip()
        parts = token.split(".")
        token_sig = parts[2] if len(parts) == 3 else token
        
        existing = db.get(RevokedToken, token_sig)
        if not existing:
            revoked = RevokedToken(
                token_sig=token_sig,
                user_id=current_user.id
            )
            db.add(revoked)
            db.commit()

    log_audit_event(
        db=db,
        event_type="AUTH_LOGOUT",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="auth",
        details={"email": current_user.email}
    )

    return {"message": "Session terminated successfully."}
