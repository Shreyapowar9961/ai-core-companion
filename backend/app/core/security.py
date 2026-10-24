import hmac
import hashlib
import json
import base64
import time
from typing import Optional, Dict, Any, List
from enum import Enum
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

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

def create_access_token(payload: Dict[str, Any], secret: str = settings.SUPABASE_JWT_SECRET, expires_in_seconds: int = 86400) -> str:
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

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)) -> AuthUser:
    if not credentials:
        # Development fallback / anonymous testing
        return AuthUser(
            id="clinician-demo-1",
            email="dr.sharma@apexcare.com",
            role=UserRole.CLINICIAN,
            facility_id="facility-apex-1",
            name="Dr. Rajesh Sharma (Lead Clinician)"
        )
    
    token = credentials.credentials
    
    # Check mock demo tokens for quick UI role switching and automated tests
    if token == "mock-token-admin":
        return AuthUser(id="admin-1", email="admin@carecompanion.org", role=UserRole.ADMIN, name="System Administrator")
    elif token == "mock-token-clinician":
        return AuthUser(id="clinician-1", email="dr.sharma@apexcare.com", role=UserRole.CLINICIAN, facility_id="facility-apex-1", name="Dr. Rajesh Sharma")
    elif token.startswith("mock-token-patient"):
        pid = token.split(":")[-1] if ":" in token else "patient-1"
        return AuthUser(id=f"user-{pid}", email=f"{pid}@patient.org", role=UserRole.PATIENT, patient_id=pid, name="Patient User")
    elif token.startswith("mock-token-caregiver"):
        pid = token.split(":")[-1] if ":" in token else "patient-1"
        return AuthUser(id=f"cg-{pid}", email=f"caregiver@{pid}.org", role=UserRole.CAREGIVER, patient_id=pid, name="Caregiver User")
    
    # Validate standard JWT (Supabase or self-issued)
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id = payload.get("sub") or payload.get("user_id") or "unknown"
    email = payload.get("email", "")
    role_str = payload.get("role", payload.get("app_metadata", {}).get("role", "CLINICIAN")).upper()
    facility_id = payload.get("facility_id")
    patient_id = payload.get("patient_id")
    name = payload.get("name", "User")
    
    try:
        role = UserRole(role_str)
    except ValueError:
        role = UserRole.CLINICIAN
        
    return AuthUser(id=user_id, email=email, role=role, facility_id=facility_id, patient_id=patient_id, name=name)

def require_roles(allowed_roles: List[UserRole]):
    def role_checker(current_user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if current_user.role == UserRole.ADMIN:
            return current_user # Admin has superuser access
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role '{current_user.role.value}'. Requires one of: {[r.value for r in allowed_roles]}"
            )
        return current_user
    return role_checker

def verify_patient_access(patient_id: str, current_user: AuthUser, patient_facility_id: Optional[str] = None):
    """
    Enforces DB-05: RBAC & Facility authorization
    - ADMIN: all
    - CLINICIAN: same facility
    - CAREGIVER: matching authorized patient_id
    - PATIENT: matching patient_id only
    """
    if current_user.role == UserRole.ADMIN:
        return
    if current_user.role == UserRole.CLINICIAN:
        if current_user.facility_id and patient_facility_id and current_user.facility_id != patient_facility_id:
            raise HTTPException(status_code=403, detail="Clinician not authorized for this facility")
        return
    if current_user.role == UserRole.PATIENT:
        if current_user.patient_id != patient_id:
            raise HTTPException(status_code=403, detail="Patients may only access their own records")
        return
    if current_user.role == UserRole.CAREGIVER:
        if current_user.patient_id != patient_id:
            raise HTTPException(status_code=403, detail="Caregiver not authorized for this patient")
        return
