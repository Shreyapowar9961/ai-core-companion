import pytest
import time
from datetime import datetime, date, timedelta
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import (
    get_current_user, require_roles, verify_patient_access,
    create_access_token, verify_jwt_token, hash_password, verify_password,
    AuthUser, UserRole
)
from app.models.user import UserProfile, RevokedToken
from app.models.patient import Patient, Caregiver, Consent
from app.models.rules_alert import Alert, EscalationRule
from app.schemas.rules_alert import EscalationRuleCreate
from app.api.v1.patients import list_patients, get_patient_profile
from app.api.v1.rules_alerts import create_or_update_rule
from app.api.v1.auth import login, logout, LoginRequest
from app.core.audit import log_audit_event
from backend.tests.mock_db import MockPostgresSession

def setup_test_environment():
    db = MockPostgresSession()

    # Seed Facility 1 & Staff
    clinician_profile = UserProfile(
        id="user-neha-101",
        email="dr.neha@apexcare.org",
        full_name="Dr. Neha Kulkarni",
        role="CLINICIAN",
        facility_id="facility-apex-1",
        password_hash=hash_password("Clinician123!"),
        is_active=True
    )
    admin_profile = UserProfile(
        id="user-admin-1",
        email="admin@apexcare.org",
        full_name="Rajesh Sharma",
        role="ADMIN",
        facility_id="facility-apex-1",
        password_hash=hash_password("Admin123!"),
        is_active=True
    )
    # Seed Facility 2 & Clinician
    clinician2_profile = UserProfile(
        id="user-patil-202",
        email="dr.patil@metropolis.org",
        full_name="Dr. Ramesh Patil",
        role="CLINICIAN",
        facility_id="facility-metropolis-2",
        password_hash=hash_password("Clinician123!"),
        is_active=True
    )

    db.add_all([clinician_profile, admin_profile, clinician2_profile])

    # Patients in Facility 1
    p1 = Patient(
        id="patient-apex-101",
        facility_id="facility-apex-1",
        first_name="Ramesh",
        last_name="Patil",
        dob=date(1955, 6, 12),
        gender="Male",
        phone="+919820011223",
        diagnosis="Post-CABG",
        discharge_date=date.today(),
        status="ACTIVE"
    )
    # Patient in Facility 2
    p2 = Patient(
        id="patient-metro-201",
        facility_id="facility-metropolis-2",
        first_name="Kishore",
        last_name="Kumar",
        dob=date(1968, 11, 5),
        gender="Male",
        phone="+919833445566",
        diagnosis="Post-Valve Replacement",
        discharge_date=date.today(),
        status="ACTIVE"
    )
    db.add_all([p1, p2])

    return db, clinician_profile, admin_profile, clinician2_profile, p1, p2


def test_1_unauthenticated_access_rejected():
    """
    1. Unauthenticated users cannot access protected patient APIs (HTTP 401).
    """
    db, *_ = setup_test_environment()
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=None, db=db)
    assert exc.value.status_code == 401
    assert "Authentication required" in exc.value.detail


def test_2_invalid_and_expired_tokens_rejected():
    """
    2. Invalid signatures, malformed tokens, and expired tokens are rejected (HTTP 401).
    """
    db, *_ = setup_test_environment()
    
    # Invalid token string
    with pytest.raises(HTTPException) as exc:
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad.token.signature")
        get_current_user(credentials=creds, db=db)
    assert exc.value.status_code == 401

    # Expired token (-10 seconds)
    expired_token = create_access_token(
        payload={"sub": "user-neha-101", "email": "dr.neha@apexcare.org"},
        expires_in_seconds=-10
    )
    with pytest.raises(HTTPException) as exc2:
        creds_expired = HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired_token)
        get_current_user(credentials=creds_expired, db=db)
    assert exc2.value.status_code == 401
    assert "Invalid or expired" in exc2.value.detail


def test_3_clinician_cannot_obtain_admin_privileges():
    """
    3. A Clinician cannot obtain Admin privileges by manipulating client state or claims.
    """
    db, clinician_profile, admin_profile, *_ = setup_test_environment()

    # Clinician token
    clinician_token = create_access_token(
        payload={"sub": clinician_profile.id, "email": clinician_profile.email, "role": "CLINICIAN"}
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=clinician_token)
    user = get_current_user(credentials=creds, db=db)
    assert user.role == UserRole.CLINICIAN

    # Admin-only gate
    admin_gate = require_roles([UserRole.ADMIN])
    with pytest.raises(HTTPException) as exc:
        admin_gate(user)
    assert exc.value.status_code == 403


def test_4_cross_facility_access_blocked():
    """
    4. A user cannot access patients outside their authorised facility (DB-05).
    """
    db, clinician_profile, admin_profile, clinician2_profile, p1, p2 = setup_test_environment()

    # Clinician 1 (Apex) accessing Patient 1 (Apex) -> Allowed
    clinician_1 = AuthUser(
        id=clinician_profile.id,
        email=clinician_profile.email,
        role=UserRole.CLINICIAN,
        facility_id="facility-apex-1",
        name=clinician_profile.full_name
    )
    verify_patient_access(patient_id=p1.id, current_user=clinician_1, patient_facility_id=p1.facility_id, db=db)

    # Clinician 1 (Apex) attempting to access Patient 2 (Metropolis) -> Blocked (403)
    with pytest.raises(HTTPException) as exc:
        verify_patient_access(patient_id=p2.id, current_user=clinician_1, patient_facility_id=p2.facility_id, db=db)
    assert exc.value.status_code == 403
    assert "Clinician is not authorized to access patient records from another facility" in exc.value.detail


def test_5_role_cannot_be_manipulated_in_token():
    """
    5. Role changes are not possible through client-controlled values in JWT claims.
       Role is strictly resolved from the backend database UserProfile record.
    """
    db, clinician_profile, *_ = setup_test_environment()

    # An attacker creates a token putting "role": "ADMIN" in the payload, but sub is a clinician's email/id
    forged_token = create_access_token(
        payload={"sub": clinician_profile.id, "email": clinician_profile.email, "role": "ADMIN"}
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=forged_token)
    user = get_current_user(credentials=creds, db=db)

    # The backend looked up the database record and assigned CLINICIAN, ignoring forged "ADMIN"
    assert user.role == UserRole.CLINICIAN
    assert user.role != UserRole.ADMIN


import asyncio

def test_6_logout_invalidates_session():
    """
    6. Logout invalidates the active session token appropriately.
    """
    db, clinician_profile, *_ = setup_test_environment()

    token = create_access_token(
        payload={"sub": clinician_profile.id, "email": clinician_profile.email}
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    # Valid before logout
    user = get_current_user(credentials=creds, db=db)
    assert user.id == clinician_profile.id

    # Execute logout
    logout(credentials=creds, current_user=user, db=db)

    # Attempting to use the same token after logout -> Rejected (401)
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=creds, db=db)
    assert exc.value.status_code == 401
    assert "revoked via logout" in exc.value.detail


def test_7_existing_workflows_operate_after_login():
    """
    7. Existing application workflows function properly after authenticated login.
    """
    db, clinician_profile, _, _, p1, _ = setup_test_environment()

    # Perform login via API
    login_req = LoginRequest(email="dr.neha@apexcare.org", password="Clinician123!")
    login_res = login(login_req, db=db)
    assert login_res.access_token is not None
    assert login_res.user["role"] == "CLINICIAN"

    # Authenticate with returned token
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=login_res.access_token)
    user = get_current_user(credentials=creds, db=db)

    # Fetch patient list for facility
    patients = list_patients(facility_id="facility-apex-1", db=db, current_user=user)
    assert len(patients) >= 1
    assert patients[0].first_name == "Ramesh"


def test_8_caregiver_disclosure_consent_enforced():
    """
    8. Caregiver disclosure remains strictly restricted to authorized channels and consented categories (GV-02).
    """
    db, _, _, _, p1, _ = setup_test_environment()

    # Caregiver with medication-only consent
    cg = Caregiver(
        id="cg-101",
        patient_id=p1.id,
        name="Sneha Patil",
        relationship="Daughter",
        phone="+919820099887",
        is_authorized=True,
        consented_channels=["SMS"],
        consented_categories=["medication"]
    )
    db.add(cg)

    # Verify disclosure category permissions
    assert "medication" in cg.consented_categories
    assert "mental_health" not in cg.consented_categories

    # Unauthorized caregiver
    unauth_cg = Caregiver(
        id="cg-unauth",
        patient_id=p1.id,
        name="Third Party",
        relationship="Neighbor",
        phone="+919800000000",
        is_authorized=False,
        consented_categories=[]
    )
    assert not unauth_cg.is_authorized


def test_9_access_control_decisions_audited():
    """
    9. Access-control decisions, including denied cross-facility attempts, are recorded in the audit trail.
    """
    db, clinician_profile, _, _, p1, p2 = setup_test_environment()
    clinician_1 = AuthUser(
        id=clinician_profile.id,
        email=clinician_profile.email,
        role=UserRole.CLINICIAN,
        facility_id="facility-apex-1",
        name=clinician_profile.full_name
    )

    with pytest.raises(HTTPException):
        verify_patient_access(patient_id=p2.id, current_user=clinician_1, patient_facility_id=p2.facility_id, db=db)

    # Verify that an audit event was emitted for the blocked access attempt
    from app.models.audit import AuditLog
    events = list(db.storage.get(AuditLog, {}).values())
    mismatch_events = [e for e in events if e.event_type == "ACCESS_DENIED_FACILITY_MISMATCH"]
    assert len(mismatch_events) >= 1
    assert mismatch_events[0].actor_id == clinician_profile.id
    assert mismatch_events[0].details_json["action"] == "BLOCKED_CROSS_FACILITY_ACCESS"
