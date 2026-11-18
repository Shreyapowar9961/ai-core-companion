"""
Tests for ON-07 (FHIR R4 Hospital Ingestion) and CV-08 (Browser Audio Recording & Playback).
PostgreSQL 18 local database ONLY. Zero SQLite.
"""

import pytest
import os
import io
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.main import app
from app.core.database import get_db, SessionLocal
from app.services.fhir_service import FHIRService, FHIRValidationError, FHIRDuplicateError
from app.models.patient import Patient, Consent, CarePlan, Caregiver
from app.models.clinical import MedicationSchedule
from app.models.conversation import CallSession, CallTurn
from app.core.security import create_access_token

client = TestClient(app)

SAMPLE_FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "type": "document",
    "entry": [
        {
            "resource": {
                "resourceType": "Patient",
                "id": "pat-fhir-101",
                "identifier": [
                    {"system": "urn:hospital:mrn", "value": "MRN-FHIR-778899"}
                ],
                "name": [
                    {
                        "use": "official",
                        "family": "Joshi",
                        "given": ["Suresh", "M."]
                    }
                ],
                "gender": "male",
                "birthDate": "1960-05-20",
                "telecom": [
                    {"system": "phone", "value": "+919833445566", "use": "mobile"},
                    {"system": "email", "value": "suresh.joshi@example.com"}
                ],
                "address": [
                    {
                        "line": ["Flat 303, Ganraj Heights", "Kothrud"],
                        "city": "Pune",
                        "state": "Maharashtra",
                        "postalCode": "411038"
                    }
                ],
                "communication": [
                    {
                        "language": {
                            "coding": [
                                {"code": "mr", "display": "Marathi"}
                            ]
                        }
                    }
                ],
                "contact": [
                    {
                        "relationship": [{"text": "Daughter"}],
                        "name": {"text": "Ananya Joshi"},
                        "telecom": [{"system": "phone", "value": "+919833445577"}]
                    }
                ]
            }
        },
        {
            "resource": {
                "resourceType": "Condition",
                "id": "cond-101",
                "clinicalStatus": {
                    "coding": [{"code": "active"}]
                },
                "code": {
                    "text": "Post-Percutaneous Transluminal Coronary Angioplasty (PTCA)"
                }
            }
        },
        {
            "resource": {
                "resourceType": "MedicationRequest",
                "id": "med-101",
                "medicationCodeableConcept": {
                    "text": "Ticagrelor 90mg"
                },
                "dosageInstruction": [
                    {
                        "text": "Take 1 tablet twice daily after meals",
                        "timing": {
                            "repeat": {
                                "frequency": 2,
                                "period": 1,
                                "periodUnit": "d"
                            }
                        },
                        "route": {"text": "Oral"}
                    }
                ]
            }
        },
        {
            "resource": {
                "resourceType": "MedicationRequest",
                "id": "med-102",
                "medicationCodeableConcept": {
                    "text": "Atorvastatin 40mg"
                },
                "dosageInstruction": [
                    {
                        "text": "Take 1 tablet once daily at bedtime",
                        "timing": {
                            "repeat": {
                                "frequency": 1,
                                "period": 1,
                                "periodUnit": "d"
                            }
                        },
                        "route": {"text": "Oral"}
                    }
                ]
            }
        },
        {
            "resource": {
                "resourceType": "CarePlan",
                "id": "cp-101",
                "description": "Post-PTCA Cardiac Rehab Plan: Low sodium diet, 10 glasses hydration, walking 25 minutes daily.",
                "activity": [
                    {
                        "detail": {
                            "description": "Hydration 10 glasses daily"
                        }
                    },
                    {
                        "detail": {
                            "description": "Cardiac walking 25 minutes daily"
                        }
                    }
                ]
            }
        }
    ]
}


@pytest.fixture
def auth_headers():
    token = create_access_token({
        "sub": "dr.neha@apexcare.org",
        "email": "dr.neha@apexcare.org",
        "role": "CLINICIAN",
        "facility_id": "facility-apex-1"
    })
    return {"Authorization": f"Bearer {token}"}


def test_fhir_bundle_parsing():
    """ON-07: Verify robust parsing of HL7 FHIR R4 Bundle into structured dictionary."""
    parsed = FHIRService.parse_bundle(SAMPLE_FHIR_BUNDLE)
    demo = parsed["demographics"]
    assert demo["first_name"] == "Suresh M."
    assert demo["last_name"] == "Joshi"
    assert demo["gender"] == "Male"
    assert demo["phone"] == "+919833445566"
    assert demo["email"] == "suresh.joshi@example.com"
    assert demo["preferred_language"] == "mr"
    assert "Kothrud" in demo["address"]
    assert "Ganraj" in demo["address"]
    assert "PTCA" in demo["diagnosis"]

    meds = parsed["medications"]
    assert len(meds) == 2
    assert meds[0]["medicine_name"] == "Ticagrelor 90mg"
    assert meds[0]["frequency"] == "TWICE_DAILY"
    assert len(meds[0]["dose_times"]) == 2

    assert meds[1]["medicine_name"] == "Atorvastatin 40mg"
    assert meds[1]["frequency"] == "ONCE_DAILY"

    caregivers = parsed["caregivers"]
    assert len(caregivers) == 1
    assert caregivers[0]["name"] == "Ananya Joshi"
    assert caregivers[0]["phone"] == "+919833445577"
    assert caregivers[0]["relationship"] == "Daughter"

    care_plan = parsed["care_plan"]
    assert care_plan["hydration_target_glasses"] == 10
    assert care_plan["activity_target_minutes"] == 30


def test_fhir_invalid_payload():
    """ON-07: Verify rejection of invalid or malformed FHIR payloads."""
    with pytest.raises(FHIRValidationError):
        FHIRService.parse_bundle({"resourceType": "Observation", "id": "obs-1"})

    with pytest.raises(FHIRValidationError):
        FHIRService.parse_bundle({"resourceType": "Bundle", "entry": []})


def test_fhir_rest_preview_and_import(auth_headers):
    """ON-07: Test FHIR preview, import, and duplicate rejection via REST API."""
    import copy
    import time

    test_bundle = copy.deepcopy(SAMPLE_FHIR_BUNDLE)
    unique_phone = f"+919833{int(time.time() * 1000) % 1000000:06d}"
    test_bundle["entry"][0]["resource"]["telecom"][0]["value"] = unique_phone

    # 1. Preview endpoint
    res_preview = client.post(
        "/api/v1/patients/import/fhir/preview",
        json=test_bundle,
        headers=auth_headers
    )
    assert res_preview.status_code == 200, res_preview.text
    preview_data = res_preview.json()
    assert preview_data["valid"] is True
    assert preview_data["is_duplicate"] is False
    assert preview_data["summary"]["patient_name"] == "Suresh M. Joshi"
    assert preview_data["summary"]["medications_count"] == 2

    # 2. Import endpoint
    res_import = client.post(
        "/api/v1/patients/import/fhir",
        json=test_bundle,
        headers=auth_headers
    )
    assert res_import.status_code == 201, res_import.text
    import_data = res_import.json()
    assert import_data["success"] is True
    patient_id = import_data["patient_id"]
    assert import_data["status"] == "ACTIVE"
    assert import_data["medications_count"] == 2

    # 3. Verify in PostgreSQL database
    db = SessionLocal()
    patient = db.get(Patient, patient_id)
    assert patient is not None
    assert patient.first_name == "Suresh M."
    assert patient.last_name == "Joshi"
    assert patient.preferred_language == "mr"
    assert patient.status == "ACTIVE"

    # Verify CarePlan & Medications
    care_plans = db.execute(select(CarePlan).where(CarePlan.patient_id == patient_id)).scalars().all()
    assert len(care_plans) == 1
    cp = care_plans[0]
    meds = db.execute(select(MedicationSchedule).where(MedicationSchedule.care_plan_id == cp.id)).scalars().all()
    assert len(meds) == 2

    # Verify Caregivers
    cgs = db.execute(select(Caregiver).where(Caregiver.patient_id == patient_id)).scalars().all()
    assert len(cgs) == 1
    assert cgs[0].name == "Ananya Joshi"
    db.close()

    # 4. Duplicate rejection (ON-07)
    res_duplicate = client.post(
        "/api/v1/patients/import/fhir",
        json=test_bundle,
        headers=auth_headers
    )
    assert res_duplicate.status_code == 409, res_duplicate.text
    dup_body = res_duplicate.json()
    assert "DUPLICATE_PATIENT" in str(dup_body)


def test_call_audio_recording_consent_and_upload(auth_headers):
    """CV-08: Test call audio recording, consent enforcement, upload and streaming."""
    db = SessionLocal()
    # Create test patient with recording consent
    patient = Patient(
        first_name="Audio",
        last_name="TestPatient",
        dob=date(1975, 3, 10),
        gender="Female",
        phone="+919855566677",
        diagnosis="Arrhythmia Monitoring",
        discharge_date=date.today(),
        status="ACTIVE"
    )
    db.add(patient)
    db.flush()

    consent = Consent(
        patient_id=patient.id,
        voice_contact=True,
        call_recording=True, # Granted
        data_processing=True
    )
    db.add(consent)

    session = CallSession(
        patient_id=patient.id,
        call_type="MORNING_CHECKIN",
        direction="OUTBOUND",
        status="IN_PROGRESS"
    )
    db.add(session)
    db.commit()
    session_id = session.id
    patient_id = patient.id
    db.close()

    # 1. Upload audio when consent granted
    sample_webm = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00"
    upload_res = client.post(
        f"/api/v1/conversation/sessions/{session_id}/audio",
        files={"file": ("test_recording.webm", io.BytesIO(sample_webm), "audio/webm")},
        headers=auth_headers
    )
    assert upload_res.status_code == 200, upload_res.text
    res_data = upload_res.json()
    assert res_data["success"] is True
    assert res_data["status"] == "RECORDED"
    assert f"/api/v1/conversation/sessions/{session_id}/audio/stream" in res_data["audio_url"]

    # 2. Stream audio
    stream_res = client.get(
        f"/api/v1/conversation/sessions/{session_id}/audio/stream",
        headers=auth_headers
    )
    assert stream_res.status_code == 200
    assert stream_res.headers.get("content-type") == "audio/webm"
    assert stream_res.content == sample_webm

    # 3. Test Consent Withholding enforcement (CV-08, GV-02)
    db = SessionLocal()
    c = db.execute(select(Consent).where(Consent.patient_id == patient_id)).scalars().first()
    c.call_recording = False # Patient revokes recording consent
    db.commit()
    db.close()

    # Attempt to upload audio to a session for patient with revoked consent
    blocked_upload = client.post(
        f"/api/v1/conversation/sessions/{session_id}/audio",
        files={"file": ("blocked.webm", io.BytesIO(sample_webm), "audio/webm")},
        headers=auth_headers
    )
    assert blocked_upload.status_code == 403, blocked_upload.text
    assert "withheld recording consent" in blocked_upload.json()["detail"]
