import pytest
from datetime import datetime, date, timedelta
from fastapi import HTTPException

from app.core.security import AuthUser, UserRole, hash_password
from app.models.patient import Patient, CarePlan
from app.models.user import UserProfile
from app.models.clinical import MedicationSchedule, MedicationLog
from app.models.monitoring import MonitoringPlan, CheckinTask, CommunicationLog, PatientFeedback
from app.models.prescription import PrescriptionUpload
from app.api.v1.auth import register_patient_account, PatientRegisterRequest, reset_password, PasswordResetRequest
from app.api.v1.patient_portal import (
    get_patient_profile, get_patient_dashboard, submit_checkin_response,
    SubmitCheckinRequest, confirm_medication_taken, ConfirmMedicationRequest,
    report_missed_medication, ReportMissedMedicationRequest,
    submit_patient_feedback, FeedbackSubmissionRequest, update_patient_language, UpdateLanguageRequest
)
from app.api.v1.prescriptions import verify_and_approve_prescription, VerifyPrescriptionRequest, VerifiedMedicationItem
from app.services.ocr_service import PrescriptionOCRService
from app.services.monitoring_scheduler import BackgroundMonitoringScheduler
from backend.tests.mock_db import MockPostgresSession

def test_patient_registration_and_backend_role_control():
    """
    Phase 2: Patient registration links to existing discharge record and strictly assigns PATIENT role.
    """
    db = MockPostgresSession()
    demo_patient = Patient(
        id="patient-reg-1",
        first_name="Sanjay",
        last_name="Rao",
        dob=date(1960, 5, 20),
        gender="Male",
        phone="+919811223344",
        diagnosis="Post-PCI Stenting",
        discharge_date=date.today(),
        status="ACTIVE"
    )
    db.add(demo_patient)

    req = PatientRegisterRequest(
        email="sanjay.rao@example.com",
        password="SecurePassword123!",
        phone="+919811223344"
    )
    resp = register_patient_account(req, db=db)

    assert resp.access_token is not None
    assert resp.user["role"] == "PATIENT"
    assert resp.user["patient_id"] == "patient-reg-1"

    # Attempting duplicate registration should raise 400
    with pytest.raises(HTTPException) as exc:
        register_patient_account(req, db=db)
    assert exc.value.status_code == 400

def test_patient_data_isolation_and_portal_dashboard():
    """
    Phase 2: Patients access only their own data via verified patient linkage.
    """
    db = MockPostgresSession()
    p1 = Patient(
        id="pat-101",
        first_name="Anil",
        last_name="Kulkarni",
        dob=date(1958, 3, 15),
        gender="Male",
        phone="+919800000001",
        diagnosis="Coronary Artery Disease",
        discharge_date=date.today() - timedelta(days=3),
        status="ACTIVE"
    )
    db.add(p1)

    med = MedicationSchedule(
        id="med-1",
        care_plan_id="cp-1",
        patient_id="pat-101",
        medicine_name="Aspirin",
        dosage="75mg",
        is_active=True
    )
    db.add(med)

    patient_user = AuthUser(
        id="usr-p1",
        email="anil@care.org",
        role=UserRole.PATIENT,
        patient_id="pat-101",
        name="Anil Kulkarni"
    )

    dashboard = get_patient_dashboard(current_user=patient_user, db=db)
    assert dashboard["patient_name"] == "Anil Kulkarni"
    assert dashboard["medication_summary"]["total"] >= 1
    assert "adherence_rate" in dashboard["medication_summary"]

    profile = get_patient_profile(current_user=patient_user, db=db)
    assert profile["diagnosis"] == "Coronary Artery Disease"

def test_medication_confirmation_and_reporting_missed():
    """
    Phase 4: Medication intake confirmation and reporting missed with structured reason.
    """
    db = MockPostgresSession()
    p1 = Patient(
        id="pat-202",
        first_name="Sunita",
        last_name="Deshmukh",
        dob=date(1965, 8, 10),
        gender="Female",
        phone="+919800000002",
        diagnosis="Heart Failure Recovery",
        discharge_date=date.today(),
        status="ACTIVE"
    )
    db.add(p1)

    patient_user = AuthUser(
        id="usr-p2",
        email="sunita@care.org",
        role=UserRole.PATIENT,
        patient_id="pat-202",
        name="Sunita Deshmukh"
    )

    # 1. Confirm dose taken
    confirm_req = ConfirmMedicationRequest(
        medicine_name="Metoprolol",
        dosage="25mg"
    )
    conf_resp = confirm_medication_taken(confirm_req, current_user=patient_user, db=db)
    assert conf_resp["status"] == "TAKEN"

    # 2. Report missed dose
    missed_req = ReportMissedMedicationRequest(
        medicine_name="Lasix",
        dosage="40mg",
        stated_reason="Experienced mild dizziness"
    )
    miss_resp = report_missed_medication(missed_req, current_user=patient_user, db=db)
    assert miss_resp["status"] == "MISSED"
    assert "dizziness" in miss_resp["reason"]

def test_checkin_questionnaire_categorisation_and_alerts():
    """
    Phase 3: Checkin submission categorisation (ROUTINE vs NEEDS_CLINICIAN_REVIEW) and alert generation.
    """
    db = MockPostgresSession()
    patient = Patient(
        id="pat-303",
        first_name="Girish",
        last_name="Jadhav",
        dob=date(1952, 11, 25),
        gender="Male",
        phone="+919800000003",
        diagnosis="Post-CABG Day 7",
        discharge_date=date.today() - timedelta(days=7),
        status="ACTIVE"
    )
    db.add(patient)

    patient_user = AuthUser(
        id="usr-p3",
        email="girish@care.org",
        role=UserRole.PATIENT,
        patient_id="pat-303",
        name="Girish Jadhav"
    )

    # 1. Normal check-in -> ROUTINE
    routine_req = SubmitCheckinRequest(
        pain_level=2,
        breathlessness="none",
        wound_status="healing_well",
        spo2=96.0
    )
    routine_resp = submit_checkin_response(routine_req, current_user=patient_user, db=db)
    assert routine_resp["category"] == "ROUTINE"
    assert routine_resp["alert_generated"] is False

    # 2. Critical SpO2 Hypoxia -> NEEDS_CLINICIAN_REVIEW and Alert
    critical_req = SubmitCheckinRequest(
        pain_level=8,
        breathlessness="severe",
        wound_status="redness",
        spo2=86.0
    )
    crit_resp = submit_checkin_response(critical_req, current_user=patient_user, db=db)
    assert crit_resp["category"] == "NEEDS_CLINICIAN_REVIEW"
    assert crit_resp["alert_generated"] is True

def test_prescription_ocr_parsing_and_doctor_verification():
    """
    Phase 4: Prescription OCR structured parsing and mandatory doctor approval workflow.
    """
    sample_rx_text = """
    Apex Heart & Recovery Institute
    Patient: Ramesh Patil | Age: 62 | Date: 2026-10-25
    Rx:
    1. Tab Atorvastatin 40mg - 1 tab at bedtime after food - 30 days
    2. Tab Metoprolol 50mg - 1 tab BD after meals - 30 days
    3. Tab Ecosprin 75mg - 1 tab OD after lunch - 30 days
    """
    meds = PrescriptionOCRService.parse_prescription_text(sample_rx_text)
    assert len(meds) >= 3
    names = [m["medicine_name"] for m in meds]
    assert "Atorvastatin" in names
    assert "Metoprolol" in names
    assert "Ecosprin" in names
    # Ensure all parsed meds are UNVERIFIED
    for m in meds:
        assert m["status"] == "UNVERIFIED"

    # Doctor verification test
    db = MockPostgresSession()
    patient = Patient(
        id="pat-404",
        first_name="Ramesh",
        last_name="Patil",
        dob=date(1956, 4, 12),
        gender="Male",
        phone="+919820011223",
        diagnosis="Post-CABG",
        discharge_date=date.today(),
        status="ACTIVE"
    )
    db.add(patient)

    upload = PrescriptionUpload(
        id="rx-upload-1",
        patient_id="pat-404",
        filename="rx_sample.pdf",
        file_path="mock/path.pdf",
        file_size=12000,
        mime_type="application/pdf",
        status="OCR_PROCESSED",
        raw_ocr_text=sample_rx_text
    )
    db.add(upload)

    doctor_user = AuthUser(
        id="doc-1",
        email="dr.neha@apexcare.org",
        role=UserRole.CLINICIAN,
        name="Dr. Neha Kulkarni"
    )

    verify_req = VerifyPrescriptionRequest(
        verified_medications=[
            VerifiedMedicationItem(
                medicine_name="Atorvastatin",
                dosage="40mg",
                frequency="Once daily",
                dose_times=["21:00"],
                instructions="Take at bedtime"
            ),
            VerifiedMedicationItem(
                medicine_name="Metoprolol",
                dosage="50mg",
                frequency="Twice daily",
                dose_times=["09:00", "20:00"]
            )
        ],
        clinician_notes="Approved discharge cardiology regimen."
    )

    result = verify_and_approve_prescription("rx-upload-1", verify_req, db=db, current_user=doctor_user)
    assert result["status"] == "VERIFIED"
    assert result["schedules_created"] == 2

def test_monitoring_scheduler_simulation_and_duplicate_prevention():
    """
    Phase 3 & 5: Scheduler generates tasks & honest simulated communications without duplicates.
    """
    db = MockPostgresSession()
    patient = Patient(
        id="pat-505",
        first_name="Vijay",
        last_name="Shinde",
        dob=date(1962, 1, 15),
        gender="Male",
        phone="+919877001122",
        diagnosis="Post-CABG Recovery",
        discharge_date=date.today(),
        status="ACTIVE"
    )
    db.add(patient)

    plan = MonitoringPlan(
        id="plan-505",
        patient_id="pat-505",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        frequency="DAILY",
        communication_channel="VOICE",
        is_active=True
    )
    db.add(plan)

    # First cycle should create checkin task & communication log
    res1 = BackgroundMonitoringScheduler.run_cycle(db=db)
    assert res1["tasks_created"] == 1

    # Second cycle on same day should prevent duplicate check-in creation
    res2 = BackgroundMonitoringScheduler.run_cycle(db=db)
    assert res2["tasks_created"] == 0

def test_patient_feedback_and_multilingual_selection():
    """
    Phase 5 & 7: Feedback collection and patient language selector.
    """
    db = MockPostgresSession()
    patient = Patient(
        id="pat-606",
        first_name="Lata",
        last_name="Mangeshkar",
        dob=date(1950, 9, 28),
        gender="Female",
        phone="+919822334455",
        diagnosis="Cardiothoracic Care",
        discharge_date=date.today(),
        preferred_language="en",
        status="ACTIVE"
    )
    db.add(patient)

    patient_user = AuthUser(
        id="usr-p6",
        email="lata@care.org",
        role=UserRole.PATIENT,
        patient_id="pat-606",
        name="Lata Mangeshkar"
    )

    # 1. Update Language to Marathi
    lang_resp = update_patient_language(UpdateLanguageRequest(language="mr"), current_user=patient_user, db=db)
    assert lang_resp["language"] == "mr"
    assert patient.preferred_language == "mr"

    # 2. Submit Feedback
    fb_req = FeedbackSubmissionRequest(
        rating=5,
        category="RECOVERY_SUPPORT",
        comments="Voice check-in was very clear and comforting."
    )
    fb_resp = submit_patient_feedback(fb_req, current_user=patient_user, db=db)
    assert fb_resp["status"] == "RECEIVED"
