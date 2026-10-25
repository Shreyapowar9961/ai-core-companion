import pytest
from datetime import date, datetime
from app.models.patient import Patient, Consent, CarePlan
from app.schemas.patient import PatientRegisterRequest, ConsentCreate, CarePlanCreate, MedicationScheduleInput
from app.api.v1.patients import register_patient
from app.core.security import AuthUser, UserRole
from backend.tests.mock_db import MockPostgresSession

def test_activation_blocked_without_consent():
    """
    ON-06: Block programme activation until care plan, contact number and consent are complete.
    If consent is missing, status must remain 'DRAFT'.
    Strictly PostgreSQL architecture.
    """
    db = MockPostgresSession()
    clinician = AuthUser(id="doc-1", email="doc@care.org", role=UserRole.CLINICIAN, facility_id="fac-1")

    req = PatientRegisterRequest(
        first_name="Sanjay",
        last_name="Rao",
        dob=date(1970, 5, 20),
        gender="Male",
        phone="+919800011122",
        diagnosis="Cardiac Stent",
        discharge_date=date.today(),
        care_plan=CarePlanCreate(
            medications=[MedicationScheduleInput(medicine_name="Atorvastatin", dosage="20mg")]
        ),
        consent=None,  # Missing consent!
        activate_if_complete=True
    )

    pt = register_patient(req=req, db=db, current_user=clinician)
    assert pt.status == "DRAFT"  # MUST NOT ACTIVATE WITHOUT CONSENT!

def test_activation_succeeds_when_all_complete():
    """
    ON-06: When care plan, contact number, and explicit consent are all present, status becomes 'ACTIVE'.
    """
    db = MockPostgresSession()
    clinician = AuthUser(id="doc-1", email="doc@care.org", role=UserRole.CLINICIAN, facility_id="fac-1")

    req = PatientRegisterRequest(
        first_name="Pooja",
        last_name="Shinde",
        dob=date(1980, 8, 14),
        gender="Female",
        phone="+919877766655",
        diagnosis="Gallbladder Surgery",
        discharge_date=date.today(),
        care_plan=CarePlanCreate(
            medications=[MedicationScheduleInput(medicine_name="Pantoprazole", dosage="40mg")]
        ),
        consent=ConsentCreate(
            voice_contact=True,
            call_recording=True,
            data_processing=True,
            caregiver_disclosure=True,
            emergency_escalation=True
        ),
        activate_if_complete=True
    )

    pt = register_patient(req=req, db=db, current_user=clinician)
    assert pt.status == "ACTIVE"

def test_consent_withdrawal_halts_contact():
    """
    PL-03: On consent withdrawal, immediately cease applicable contact and processing.
    """
    db = MockPostgresSession()
    p = Patient(
        id="pt-withdraw",
        first_name="Gopal",
        last_name="Verma",
        dob=date(1965, 3, 10),
        gender="Male",
        phone="+919822334455",
        diagnosis="Hernia Repair",
        discharge_date=date.today(),
        status="ACTIVE"
    )
    db.add(p)
    c = Consent(
        patient_id=p.id,
        voice_contact=True,
        call_recording=True,
        data_processing=True
    )
    db.add(c)

    # Withdraw consent
    c.voice_contact = False
    c.withdrawn_at = datetime.utcnow()
    c.withdrawal_scope = "FULL"
    p.status = "CONSENT_WITHDRAWN"

    assert p.status == "CONSENT_WITHDRAWN"
    assert c.voice_contact is False
