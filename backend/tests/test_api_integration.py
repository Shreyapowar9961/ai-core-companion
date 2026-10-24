import pytest
from starlette.testclient import TestClient
from app.main import app
from app.core.security import create_access_token, UserRole

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

def test_rbac_admin_clinician_access():
    """
    DB-05: Enforce role-based access so users see only patients and data appropriate to their role and facility.
    """
    # 1. Clinician token
    clinician_token = create_access_token({
        "sub": "doc-101",
        "email": "dr.sharma@apexcare.com",
        "role": UserRole.CLINICIAN.value,
        "facility_id": "facility-apex-1",
        "name": "Dr. Sharma"
    })
    headers = {"Authorization": f"Bearer {clinician_token}"}

    resp = client.get("/api/v1/patients/", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # 2. Unauthorized role attempting to configure clinician rules (ES-01)
    patient_token = create_access_token({
        "sub": "patient-99",
        "email": "patient@care.org",
        "role": UserRole.PATIENT.value,
        "patient_id": "patient-99"
    })
    patient_headers = {"Authorization": f"Bearer {patient_token}"}

    rule_resp = client.post(
        "/api/v1/rules-alerts/rules",
        headers=patient_headers,
        json={
            "code": "RULE_UNAUTHORIZED",
            "name": "Unauthorized Test",
            "category": "VITALS",
            "severity": "CRITICAL",
            "condition_json": {},
            "action_json": {}
        }
    )
    assert rule_resp.status_code == 403 # Forbidden! Only Clinician or Admin permitted

def test_full_alert_resolution_lifecycle():
    """
    DB-04, ES-07: Acknowledge and Resolve alert with explicit named user action notes.
    """
    admin_token = create_access_token({
        "sub": "admin-1",
        "email": "admin@care.org",
        "role": UserRole.ADMIN.value,
        "name": "Admin Officer"
    })
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Fetch alerts
    alerts_resp = client.get("/api/v1/rules-alerts/alerts", headers=headers)
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert len(alerts) > 0

    target_alert = alerts[0]
    alert_id = target_alert["id"]

    # 1. Acknowledge alert
    ack_resp = client.post(
        f"/api/v1/rules-alerts/alerts/{alert_id}/acknowledge",
        headers=headers,
        json={"notes": "Reviewed with attending cardiologist."}
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "ACKNOWLEDGED"

    # 2. Resolve alert with explicit clinical action notes (DB-04, ES-07)
    res_resp = client.post(
        f"/api/v1/rules-alerts/alerts/{alert_id}/resolve",
        headers=headers,
        json={"resolution_action_notes": "Patient contacted via phone. Advised rest, hydration, and took follow-up SpO2 reading of 97%."}
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["status"] == "RESOLVED"
    assert "Patient contacted via phone" in res_resp.json()["resolution_action_notes"]

def test_journey_reconstruction():
    """
    GV-05: Enable reconstruction of a patient's complete interaction history for any period.
    """
    admin_token = create_access_token({
        "sub": "admin-1",
        "email": "admin@care.org",
        "role": UserRole.ADMIN.value,
        "name": "Admin Officer"
    })
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.get("/api/v1/audit/journey/patient-demo-1", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert isinstance(data["events"], list)
