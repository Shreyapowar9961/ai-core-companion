import pytest
from datetime import datetime, date, timedelta
from fastapi import HTTPException
from app.main import health_check
from app.core.security import AuthUser, UserRole, require_roles, verify_patient_access
from app.models.patient import Patient
from app.models.rules_alert import Alert
from app.models.audit import AuditLog
from app.schemas.rules_alert import EscalationRuleCreate, AlertAcknowledgeRequest, AlertResolveRequest
from app.api.v1.patients import list_patients, get_patient_profile
from app.api.v1.rules_alerts import list_alerts, acknowledge_alert, resolve_alert, create_or_update_rule
from app.core.audit import reconstruct_patient_journey
from backend.tests.mock_db import MockPostgresSession

def test_health_endpoint():
    resp = health_check()
    assert resp["status"] == "healthy"
    assert resp["database"] == "PostgreSQL (Supabase)"

def test_rbac_admin_clinician_access():
    """
    DB-05: Enforce role-based access so users see only patients and data appropriate to their role and facility.
    """
    db = MockPostgresSession()
    demo_patient = Patient(
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
    db.add(demo_patient)

    # 1. Clinician can list patients in their facility
    clinician = AuthUser(
        id="doc-101",
        email="dr.sharma@apexcare.com",
        role=UserRole.CLINICIAN,
        facility_id="facility-apex-1",
        name="Dr. Sharma"
    )
    patients = list_patients(facility_id="facility-apex-1", db=db, current_user=clinician)
    assert len(patients) >= 1
    assert patients[0].first_name == "Ramesh"

    # 2. Patient attempting unauthorized action (e.g. creating clinician rule) must be blocked (403)
    patient_user = AuthUser(
        id="patient-99",
        email="patient@care.org",
        role=UserRole.PATIENT,
        patient_id="patient-99"
    )
    role_checker = require_roles([UserRole.CLINICIAN, UserRole.ADMIN])
    with pytest.raises(HTTPException) as excinfo:
        role_checker(patient_user)
    assert excinfo.value.status_code == 403

def test_full_alert_resolution_lifecycle():
    """
    DB-04, ES-07: Acknowledge and Resolve alert with explicit named user action notes.
    """
    db = MockPostgresSession()
    alert = Alert(
        id="alert-lifecycle-1",
        patient_id="patient-apex-101",
        rule_code="RULE_VITALS_SPO2_CRITICAL",
        severity="CRITICAL",
        title="Critical Low SpO2 Breach",
        description="Oxygen saturation dropped to 86%",
        status="OPEN",
        sla_due_at=datetime.utcnow() + timedelta(minutes=15)
    )
    db.add(alert)

    admin = AuthUser(
        id="admin-1",
        email="admin@care.org",
        role=UserRole.ADMIN,
        name="Admin Officer"
    )

    # 1. Acknowledge alert
    ack_req = AlertAcknowledgeRequest(notes="Reviewed with attending cardiologist.")
    ack_res = acknowledge_alert("alert-lifecycle-1", ack_req, db=db, current_user=admin)
    assert ack_res.status == "ACKNOWLEDGED"
    assert ack_res.acknowledged_by is not None

    # 2. Resolve alert with explicit clinical action notes
    resolve_req = AlertResolveRequest(
        resolution_action_notes="Patient contacted via phone. Advised rest, hydration, and took follow-up SpO2 reading of 97%."
    )
    res_result = resolve_alert("alert-lifecycle-1", resolve_req, db=db, current_user=admin)
    assert res_result.status == "RESOLVED"
    assert "Advised rest" in res_result.resolution_action_notes

def test_journey_reconstruction():
    """
    GV-05: Enable reconstruction of a patient's complete interaction history for any period.
    """
    db = MockPostgresSession()
    audit_entry = AuditLog(
        id="audit-j-1",
        event_type="CALL_COMPLETED",
        patient_id="pt-journey-test",
        actor_id="AI_COMPANION",
        actor_role="SYSTEM",
        resource="call_session",
        details_json={"disposition": "COMPLETED", "duration_seconds": 180},
        created_at=datetime.utcnow()
    )
    db.add(audit_entry)

    events = reconstruct_patient_journey(db, "pt-journey-test")
    assert isinstance(events, list)
    assert len(events) >= 1
    assert events[0]["type"] == "AUDIT_EVENT"
    assert events[0]["subtype"] == "CALL_COMPLETED"
