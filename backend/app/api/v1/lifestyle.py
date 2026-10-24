from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, verify_patient_access
from app.models.clinical import LifestyleLog
from app.models.patient import Patient, CarePlan
from app.schemas.clinical import LifestyleLogCreate, LifestyleLogResponse
from app.core.audit import log_audit_event

router = APIRouter(prefix="/lifestyle", tags=["Lifestyle & Care Plan Adherence"])

@router.post("/patient/{patient_id}/log", response_model=LifestyleLogResponse, status_code=status.HTTP_201_CREATED)
def log_lifestyle_activity(
    patient_id: str,
    req: LifestyleLogCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    verify_patient_access(patient_id, current_user, patient.facility_id)

    log_entry = LifestyleLog(
        patient_id=patient_id,
        log_type=req.log_type,
        target_value=req.target_value,
        actual_value=req.actual_value,
        unit=req.unit,
        completion_status=req.completion_status,
        reported_pain_difficulty=req.reported_pain_difficulty,
        notes=req.notes,
        recorded_at=datetime.utcnow()
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    log_audit_event(
        db=db,
        event_type="LIFESTYLE_LOG_RECORDED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="lifestyle_log",
        details={"type": req.log_type, "status": req.completion_status},
        patient_id=patient_id
    )

    return log_entry

@router.get("/patient/{patient_id}/logs", response_model=List[LifestyleLogResponse])
def list_lifestyle_logs(
    patient_id: str,
    log_type: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    stmt = select(LifestyleLog).where(LifestyleLog.patient_id == patient_id)
    if log_type:
        stmt = stmt.where(LifestyleLog.log_type == log_type)
    stmt = stmt.order_by(desc(LifestyleLog.recorded_at)).limit(limit)

    return db.execute(stmt).scalars().all()
