from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, UserRole, require_roles, verify_patient_access
from app.core.audit import log_audit_event, log_config_audit
from app.models.patient import Patient, Facility, Caregiver, Consent, CarePlan
from app.models.clinical import MedicationSchedule, VitalsThreshold
from app.schemas.patient import (
    PatientRegisterRequest, PatientUpdateRequest, PatientResponse,
    CaregiverCreate, ConsentCreate, PatientPauseResumeRequest, ConsentWithdrawRequest
)

router = APIRouter(prefix="/patients", tags=["Patients & Onboarding"])

@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def register_patient(
    req: PatientRegisterRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    """
    ON-01 to ON-06: Register patient at discharge with demographics, care plan,
    caregivers, operating preferences, and explicit consent.
    BLOCKS PROGRAMME ACTIVATION until care plan, contact number, and consent are complete (ON-06).
    """
    facility_id = req.facility_id or current_user.facility_id or "facility-apex-1"

    if not req.phone or len(req.phone.strip()) < 7:
        raise HTTPException(status_code=400, detail="Valid contact number is required")

    is_consent_complete = (
        req.consent is not None and
        req.consent.voice_contact and
        req.consent.call_recording and
        req.consent.data_processing
    )
    is_care_plan_complete = (
        req.care_plan is not None and
        len(req.care_plan.medications) > 0
    )

    initial_status = "ACTIVE" if (req.activate_if_complete and is_consent_complete and is_care_plan_complete) else "DRAFT"

    patient = Patient(
        facility_id=facility_id,
        first_name=req.first_name,
        last_name=req.last_name,
        dob=req.dob,
        gender=req.gender,
        phone=req.phone,
        email=req.email,
        address=req.address,
        emergency_contact_phone=req.emergency_contact_phone,
        diagnosis=req.diagnosis,
        discharge_date=req.discharge_date,
        programme_duration_days=req.programme_duration_days,
        preferred_language=req.preferred_language,
        status=initial_status,
        call_window_start=req.call_window_start,
        call_window_end=req.call_window_end,
        checkin_morning_time=req.checkin_morning_time,
        checkin_evening_time=req.checkin_evening_time,
        dnd_start=req.dnd_start,
        dnd_end=req.dnd_end,
        retry_limit=req.retry_limit,
        max_deferrals=req.max_deferrals,
        treating_doctor_name=req.treating_doctor_name,
        treating_doctor_phone=req.treating_doctor_phone,
        treating_doctor_specialty=req.treating_doctor_specialty,
        created_at=datetime.utcnow()
    )
    db.add(patient)
    db.flush()

    if req.consent:
        consent = Consent(
            patient_id=patient.id,
            voice_contact=req.consent.voice_contact,
            call_recording=req.consent.call_recording,
            data_processing=req.consent.data_processing,
            caregiver_disclosure=req.consent.caregiver_disclosure,
            emergency_escalation=req.consent.emergency_escalation,
            consented_at=datetime.utcnow() if req.consent.voice_contact else None,
            consent_notes=req.consent.consent_notes
        )
        db.add(consent)
    else:
        consent = Consent(patient_id=patient.id)
        db.add(consent)

    for cg_data in req.caregivers:
        cg = Caregiver(
            patient_id=patient.id,
            name=cg_data.name,
            relationship=cg_data.relationship,
            phone=cg_data.phone,
            email=cg_data.email,
            is_authorized=cg_data.is_authorized,
            consented_channels=cg_data.consented_channels,
            consented_categories=cg_data.consented_categories
        )
        db.add(cg)

    if req.care_plan:
        cp = CarePlan(
            patient_id=patient.id,
            diet_instructions=req.care_plan.diet_instructions,
            hydration_target_glasses=req.care_plan.hydration_target_glasses,
            hydration_interval_hours=req.care_plan.hydration_interval_hours,
            activity_target_minutes=req.care_plan.activity_target_minutes,
            activity_target_steps=req.care_plan.activity_target_steps,
            physiotherapy_instructions=req.care_plan.physiotherapy_instructions
        )
        db.add(cp)
        db.flush()

        for med in req.care_plan.medications:
            ms = MedicationSchedule(
                care_plan_id=cp.id,
                patient_id=patient.id,
                medicine_name=med.medicine_name,
                dosage=med.dosage,
                frequency=med.frequency,
                dose_times=med.dose_times,
                instructions=med.instructions,
                route=med.route,
                effective_start_date=req.discharge_date,
                is_active=True
            )
            db.add(ms)

        for vt in req.care_plan.vitals_thresholds:
            thresh = VitalsThreshold(
                care_plan_id=cp.id,
                patient_id=patient.id,
                vital_type=vt.vital_type,
                unit=vt.unit,
                plausible_min=vt.plausible_min,
                plausible_max=vt.plausible_max,
                normal_min=vt.normal_min,
                normal_max=vt.normal_max,
                warning_min=vt.warning_min,
                warning_max=vt.warning_max,
                critical_min=vt.critical_min,
                critical_max=vt.critical_max
            )
            db.add(thresh)

    db.commit()
    db.refresh(patient)

    log_audit_event(
        db=db,
        event_type="PATIENT_ONBOARDED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="patient",
        details={
            "patient_id": patient.id,
            "status": patient.status,
            "consent_granted": is_consent_complete,
            "care_plan_provided": is_care_plan_complete
        },
        patient_id=patient.id
    )

    return patient

@router.get("/", response_model=List[PatientResponse])
def list_patients(
    facility_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    stmt = select(Patient)
    if current_user.role == UserRole.CLINICIAN:
        fac = facility_id or current_user.facility_id
        if fac:
            stmt = stmt.where(Patient.facility_id == fac)
    elif current_user.role == UserRole.PATIENT:
        stmt = stmt.where(Patient.id == current_user.patient_id)
    elif current_user.role == UserRole.CAREGIVER:
        stmt = stmt.where(Patient.id == current_user.patient_id)

    if status_filter:
        stmt = stmt.where(Patient.status == status_filter)

    results = db.execute(stmt).scalars().all()
    return results

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_profile(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    verify_patient_access(patient_id, current_user, patient.facility_id)
    return patient

@router.post("/{patient_id}/pause")
def pause_patient(
    patient_id: str,
    req: PatientPauseResumeRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    old_status = patient.status
    patient.status = "PAUSED"
    patient.paused_at = datetime.utcnow()
    patient.pause_reason = req.reason or "Hospital readmission or clinician hold"
    db.commit()

    log_config_audit(
        db=db,
        config_type="SCHEDULE",
        item_id=patient.id,
        changed_by=current_user.id,
        old_value={"status": old_status},
        new_value={"status": "PAUSED", "pause_reason": patient.pause_reason},
        change_reason=req.reason
    )
    return {"message": "Programme paused successfully", "status": patient.status}

@router.post("/{patient_id}/resume")
def resume_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    old_status = patient.status
    patient.status = "ACTIVE"
    patient.paused_at = None
    patient.pause_reason = None
    db.commit()

    log_config_audit(
        db=db,
        config_type="SCHEDULE",
        item_id=patient.id,
        changed_by=current_user.id,
        old_value={"status": old_status},
        new_value={"status": "ACTIVE"},
        change_reason="Programme resumed"
    )
    return {"message": "Programme resumed successfully", "status": patient.status}

@router.post("/{patient_id}/complete")
def complete_patient_programme(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient.status = "COMPLETED"
    patient.completed_at = datetime.utcnow()
    db.commit()

    log_audit_event(
        db=db,
        event_type="PROGRAMME_COMPLETED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="patient",
        details={"completed_at": patient.completed_at.isoformat()},
        patient_id=patient.id
    )
    return {"message": "Programme completed. All scheduled calls stopped.", "status": "COMPLETED"}

@router.post("/{patient_id}/consent/withdraw")
def withdraw_consent(
    patient_id: str,
    req: ConsentWithdrawRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    consent_stmt = select(Consent).where(Consent.patient_id == patient_id)
    consent = db.execute(consent_stmt).scalars().first()
    if not consent:
        raise HTTPException(status_code=404, detail="Consent record not found")

    consent.withdrawn_at = datetime.utcnow()
    consent.withdrawal_scope = req.scope

    if req.scope == "FULL":
        consent.voice_contact = False
        consent.call_recording = False
        consent.data_processing = False
        consent.caregiver_disclosure = False
        patient.status = "CONSENT_WITHDRAWN"
    elif req.scope == "CAREGIVER_ONLY":
        consent.caregiver_disclosure = False
    elif req.scope == "CALLS_ONLY":
        consent.voice_contact = False

    db.commit()

    log_audit_event(
        db=db,
        event_type="CONSENT_WITHDRAWN",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="consent",
        details={"scope": req.scope, "reason": req.reason},
        patient_id=patient.id
    )

    return {
        "message": f"Consent withdrawal ({req.scope}) processed immediately.",
        "scope": req.scope,
        "patient_status": patient.status
    }

@router.post("/import-his")
def import_from_his(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    name_parts = data.get("patient_name", "HIS Patient").split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else "Discharged"

    reg_req = PatientRegisterRequest(
        first_name=first_name,
        last_name=last_name,
        dob=date(1955, 6, 15),
        gender=data.get("gender", "Female"),
        phone=data.get("phone", "+919876543210"),
        diagnosis=data.get("diagnosis", "Post-CABG Cardiac Recovery"),
        discharge_date=date.today(),
        programme_duration_days=30,
        preferred_language=data.get("preferred_language", "hi"),
        treating_doctor_name=data.get("doctor_name", "Dr. V. Kulkarni"),
        care_plan=None,
        consent=ConsentCreate(
            voice_contact=True,
            call_recording=True,
            data_processing=True,
            caregiver_disclosure=True,
            emergency_escalation=True
        ),
        activate_if_complete=False
    )

    result = register_patient(reg_req, db, current_user)
    return {"message": "HIS import successful. Review draft care-plan.", "patient_id": result.id}
