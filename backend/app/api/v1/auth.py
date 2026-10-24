from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from app.core.security import get_current_user, AuthUser, UserRole, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])

class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = "password"
    role: Optional[str] = "CLINICIAN" # CLINICIAN, ADMIN, CAREGIVER, PATIENT
    facility_id: Optional[str] = "facility-apex-1"
    patient_id: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """
    Authenticate user and issue JWT token compatible with Supabase Auth schema.
    Also supports demo role switching for interactive demonstration and testing.
    """
    role_enum = UserRole.CLINICIAN
    try:
        role_enum = UserRole(req.role.upper())
    except Exception:
        pass

    user_payload = {
        "sub": f"user-{req.email.split('@')[0]}",
        "email": req.email,
        "role": role_enum.value,
        "facility_id": req.facility_id,
        "patient_id": req.patient_id,
        "name": req.email.split("@")[0].replace(".", " ").title()
    }
    
    token = create_access_token(user_payload)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=user_payload
    )

@router.get("/me")
async def get_me(current_user: AuthUser = Depends(get_current_user)):
    """
    Returns authenticated user context and assigned RBAC role (DB-05).
    """
    return current_user.to_dict()
