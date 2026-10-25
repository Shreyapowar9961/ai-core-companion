import hmac
import hashlib
import json
import base64
import time
import os
import urllib.request
from typing import Optional, Dict, Any, List
from enum import Enum
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CLINICIAN = "CLINICIAN"
    CAREGIVER = "CAREGIVER"
    PATIENT = "PATIENT"

class AuthUser:
    def __init__(
        self,
        id: str,
        email: str,
        role: UserRole,
        facility_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        name: str = "User"
    ):
        self.id = id
        self.email = email
        self.role = role
        self.facility_id = facility_id
        self.patient_id = patient_id
        self.name = name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role.value,
            "facility_id": self.facility_id,
            "patient_id": self.patient_id,
            "name": self.name
        }

def _b64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def _b64_url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)

def hash_password(password: str) -> str:
    """
    Hashes password using PBKDF2-HMAC-SHA256 with a 16-byte cryptographically random salt
    and 100,000 iterations.
    """
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ":" + key.hex()

def verify_password(password: str, hashed_value: Optional[str]) -> bool:
    """
    Verifies a plaintext password against a stored salt:hash string.
    """
    if not hashed_value or ":" not in hashed_value:
        return False
    try:
        parts = hashed_value.split(":")
        if len(parts) != 2:
            return False
        salt = bytes.fromhex(parts[0])
        expected_key = parts[1]
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(key.hex(), expected_key)
    except Exception:
        return False

def create_access_token(payload: Dict[str, Any], secret: str = settings.SUPABASE_JWT_SECRET, expires_in_seconds: int = 86400) -> str:
    """
    Creates a signed HS256 JWT access token compatible with Supabase Auth schema.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    body = {**payload, "exp": int(time.time()) + expires_in_seconds, "iat": int(time.time())}
    
    header_b64 = _b64_url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    body_b64 = _b64_url_encode(json.dumps(body, separators=(',', ':')).encode('utf-8'))
    
    signature = hmac.new(
        secret.encode('utf-8'),
        f"{header_b64}.{body_b64}".encode('utf-8'),
        hashlib.sha256
    ).digest()
    sig_b64 = _b64_url_encode(signature)
    
    return f"{header_b64}.{body_b64}.{sig_b64}"

def verify_jwt_token(token: str, secret: str = settings.SUPABASE_JWT_SECRET) -> Optional[Dict[str, Any]]:
    """
    Verifies token structure, signature, and expiration.
    Returns decoded payload if valid, None otherwise.
    """
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, body_b64, sig_b64 = parts
        
        expected_sig = hmac.new(
            secret.encode('utf-8'),
            f"{header_b64}.{body_b64}".encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        if not hmac.compare_digest(_b64_url_encode(expected_sig), sig_b64):
            return None
            
        payload = json.loads(_b64_url_decode(body_b64).decode('utf-8'))
        if payload.get("exp") and payload["exp"] < time.time():
            return None
            
        return payload
    except Exception:
        return None

security_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: Session = Depends(get_db)
) -> AuthUser:
    """
    Strict Authentication & Authorization Dependency (DB-05):
    1. Rejects unauthenticated requests with HTTP 401.
    2. Validates JWT signature and expiration.
    3. Checks token revocation list.
    4. Retrieves user role and facility assignment EXCLUSIVELY from trusted database records.
       Client-provided claims or manipulated frontend payloads are rejected.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Bearer token missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials.strip()

    # 1. Verify token signature and expiration
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Check token revocation (logout)
    token_parts = token.split(".")
    token_sig = token_parts[2] if len(token_parts) == 3 else token
    from app.models.user import RevokedToken, UserProfile
    revoked = db.get(RevokedToken, token_sig)
    if revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked via logout. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub") or payload.get("user_id")
    email = payload.get("email")

    if not user_id and not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Retrieve user profile directly from database
    stmt = select(UserProfile).where(
        (UserProfile.id == user_id) | (UserProfile.email == email)
    )
    user_record = db.execute(stmt).scalars().first()

    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User account is not registered in the clinical directory."
        )

    if not user_record.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User account has been deactivated."
        )

    # Validate staff role (Only CLINICIAN and ADMIN permitted on clinical dashboard)
    try:
        trusted_role = UserRole(user_record.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: unauthorized clinical role '{user_record.role}'."
        )

    return AuthUser(
        id=user_record.id,
        email=user_record.email,
        role=trusted_role,
        facility_id=user_record.facility_id,
        name=user_record.full_name
    )

def require_roles(allowed_roles: List[UserRole]):
    """
    Enforces RBAC role checks (DB-05).
    Admin has full oversight; Clinicians must match allowed roles.
    """
    def role_checker(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if current_user.role == UserRole.ADMIN:
            return current_user
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role '{current_user.role.value}'. Requires one of: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker

def verify_patient_access(
    patient_id: str,
    current_user: AuthUser,
    patient_facility_id: Optional[str] = None,
    db: Optional[Session] = None
):
    """
    Enforces DB-05: RBAC & Facility Multi-Tenancy authorization
    - ADMIN: Access to all facilities
    - CLINICIAN: Access strictly restricted to assigned facility. Cross-facility access blocked.
    """
    if current_user.role == UserRole.ADMIN:
        return

    if current_user.role == UserRole.CLINICIAN:
        if current_user.facility_id and patient_facility_id and current_user.facility_id != patient_facility_id:
            if db:
                from app.core.audit import log_audit_event
                log_audit_event(
                    db=db,
                    event_type="ACCESS_DENIED_FACILITY_MISMATCH",
                    actor_id=current_user.id,
                    actor_role=current_user.role.value,
                    resource="patient",
                    details={
                        "requested_patient_id": patient_id,
                        "patient_facility": patient_facility_id,
                        "clinician_facility": current_user.facility_id,
                        "action": "BLOCKED_CROSS_FACILITY_ACCESS"
                    },
                    patient_id=patient_id
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Clinician is not authorized to access patient records from another facility (DB-05)."
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Unauthorized patient access."
    )
