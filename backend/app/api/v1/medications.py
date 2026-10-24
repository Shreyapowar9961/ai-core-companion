from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, UserRole, require_roles, verify_patient_access
from app.models.clinical import MedicationSchedule, MedicationLog
from app.models.patient import Patient, CarePlan
from app.schemas.clinical import (
    MedicationScheduleCreate, MedicationScheduleResponse,
    MedicationLogCreate, MedicationLogResponse
)
from app.services.rules_engine import RulesEngine
from app.core.audit import log_audit_event, log_config_audit

router = APIRouter(prefix="/medications", tags=["Medications & Adherence"])

@router.get("/patient/{patient_id}/schedules", response_model=List[MedicationScheduleResponse])
def list_medication_schedules(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    stmt = select(MedicationSchedule).where(
        MedicationSchedule.patient_id == patient_id,
        MedicationSchedule.is_active == True
    )
    return db.execute(stmt).scalars().all()

@router.post("/patient/{patient_id}/schedules", response_model=MedicationScheduleResponse, status_code=status.HTTP_201_CREATED)
def add_or_update_medication_schedule(
    patient_id: str,
    req: MedicationScheduleCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    ms = MedicationSchedule(
        care_plan_id=req.care_plan_id,
        patient_id=patient_id,
        medicine_name=req.medicine_name,
        dosage=req.dosage,
        frequency=req.frequency,
        dose_times=req.dose_times,
        instructions=req.instructions,
        route=req.route,
        effective_start_date=req.effective_start_date,
        effective_end_date=req.effective_end_date,
        is_active=True
    )
    db.add(ms)
    db.commit()
    db.refresh(ms)

    log_config_audit(
        db=db,
        config_type="SCHEDULE",
        item_id=ms.id,
        changed_by=current_user.id,
        new_value={"medicine_name": ms.medicine_name, "dosage": ms.dosage, "effective": str(ms.effective_start_date)},
        change_reason="Prescription schedule update"
    )

    return ms

@router.post("/patient/{patient_id}/log", response_model=MedicationLogResponse, status_code=status.HTTP_201_CREATED)
def log_medication_dose(
    patient_id: str,
    req: MedicationLogCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if req.status == "DEFERRED" and req.deferral_count >= patient.max_deferrals:
        final_status = "MISSED"
        reason = f"Max deferrals ({patient.max_deferrals}) exceeded without dose taken."
    else:
        final_status = req.status
        reason = req.stated_reason

    log_entry = MedicationLog(
        patient_id=patient_id,
        medication_schedule_id=req.medication_schedule_id,
        medicine_name=req.medicine_name,
        dosage=req.dosage,
        scheduled_time=req.scheduled_time,
        actual_time=datetime.utcnow() if final_status == "TAKEN" else req.actual_time,
        status=final_status,
        stated_reason=reason,
        deferral_count=req.deferral_count,
        recorded_via=req.recorded_via
    )
    db.add(log_entry)
    db.flush()

    if final_status in ["MISSED", "DEFERRED"]:
        RulesEngine.evaluate_medication_miss(db, patient_id, req.medicine_name)

    db.commit()
    db.refresh(log_entry)

    log_audit_event(
        db=db,
        event_type="MEDICATION_DOSE_RECORDED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="medication_log",
        details={"status": final_status, "medicine": req.medicine_name},
        patient_id=patient_id
    )

    return log_entry

@router.get("/patient/{patient_id}/next")
def get_next_medication(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    stmt = select(MedicationSchedule).where(
        MedicationSchedule.patient_id == patient_id,
        MedicationSchedule.is_active == True
    ).order_by(MedicationSchedule.created_at)
    meds = db.execute(stmt).scalars().all()

    if not meds:
        return {"has_next": False, "message": "No active prescribed medications found."}

    next_med = meds[0]
    return {
        "has_next": True,
        "medicine_name": next_med.medicine_name,
        "dosage": next_med.dosage,
        "dose_times": next_med.dose_times,
        "instructions": next_med.instructions
    }

@router.get("/patient/{patient_id}/adherence")
def calculate_adherence(
    patient_id: str,
    period_days: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    stmt = select(MedicationLog).where(MedicationLog.patient_id == patient_id)
    if period_days:
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        stmt = stmt.where(MedicationLog.scheduled_time >= cutoff)

    logs = db.execute(stmt).scalars().all()
    if not logs:
        return {
            "patient_id": patient_id,
            "period_days": period_days or "programme_to_date",
            "total_doses": 0,
            "taken_doses": 0,
            "missed_doses": 0,
            "adherence_percentage": 100.0
        }

    total = len(logs)
    taken = sum(1 for m in logs if m.status == "TAKEN")
    missed = sum(1 for m in logs if m.status in ["MISSED", "DEFERRED"])
    pct = round((taken / total) * 100.0, 1)

    return {
        "patient_id": patient_id,
        "period_days": period_days or "programme_to_date",
        "total_doses": total,
        "taken_doses": taken,
        "missed_doses": missed,
        "adherence_percentage": pct
    }
