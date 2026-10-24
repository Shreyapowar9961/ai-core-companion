from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, UserRole, require_roles, verify_patient_access
from app.models.clinical import VitalReading, VitalsThreshold
from app.models.patient import Patient
from app.schemas.clinical import VitalReadingCreate, VitalReadingResponse, VitalsThresholdResponse
from app.schemas.patient import VitalsThresholdInput
from app.services.rules_engine import RulesEngine
from app.core.audit import log_audit_event, log_config_audit

router = APIRouter(prefix="/vitals", tags=["Vitals Monitoring"])

@router.post("/patient/{patient_id}/reading", response_model=VitalReadingResponse, status_code=status.HTTP_201_CREATED)
def record_vital_reading(
    patient_id: str,
    req: VitalReadingCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    verify_patient_access(patient_id, current_user, patient.facility_id)

    vital_status, alert = RulesEngine.evaluate_vital_reading(
        db=db,
        patient_id=patient_id,
        vital_type=req.vital_type,
        value=req.value,
        secondary_value=req.secondary_value,
        unit=req.unit
    )

    if vital_status == "IMPLAUSIBLE":
        raise HTTPException(
            status_code=400,
            detail=f"Value {req.value} {req.unit} is outside biologically plausible boundaries. Please verify and re-enter."
        )

    reading = VitalReading(
        patient_id=patient_id,
        call_session_id=req.call_session_id,
        vital_type=req.vital_type,
        value=req.value,
        secondary_value=req.secondary_value,
        unit=req.unit,
        status=vital_status,
        voice_confirmed=req.voice_confirmed,
        notes=req.notes,
        recorded_at=datetime.utcnow()
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    log_audit_event(
        db=db,
        event_type="VITAL_READING_RECORDED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="vital_reading",
        details={
            "vital_type": req.vital_type,
            "value": req.value,
            "status": vital_status,
            "alert_created": alert is not None
        },
        patient_id=patient_id
    )

    return reading

@router.get("/patient/{patient_id}/readings", response_model=List[VitalReadingResponse])
def list_patient_vitals(
    patient_id: str,
    vital_type: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    stmt = select(VitalReading).where(VitalReading.patient_id == patient_id)
    if vital_type:
        stmt = stmt.where(VitalReading.vital_type == vital_type)
    stmt = stmt.order_by(desc(VitalReading.recorded_at)).limit(limit)

    return db.execute(stmt).scalars().all()

@router.post("/patient/{patient_id}/thresholds")
def configure_vitals_threshold(
    patient_id: str,
    req: VitalsThresholdInput,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    stmt = select(VitalsThreshold).where(
        VitalsThreshold.patient_id == patient_id,
        VitalsThreshold.vital_type == req.vital_type
    )
    thresh = db.execute(stmt).scalars().first()

    old_val = None
    if not thresh:
        thresh = VitalsThreshold(
            care_plan_id="default-plan",
            patient_id=patient_id,
            vital_type=req.vital_type,
            unit=req.unit,
            plausible_min=req.plausible_min,
            plausible_max=req.plausible_max,
            normal_min=req.normal_min,
            normal_max=req.normal_max,
            warning_min=req.warning_min,
            warning_max=req.warning_max,
            critical_min=req.critical_min,
            critical_max=req.critical_max
        )
        db.add(thresh)
    else:
        old_val = {
            "warning_min": thresh.warning_min,
            "warning_max": thresh.warning_max,
            "critical_min": thresh.critical_min,
            "critical_max": thresh.critical_max
        }
        thresh.warning_min = req.warning_min
        thresh.warning_max = req.warning_max
        thresh.critical_min = req.critical_min
        thresh.critical_max = req.critical_max

    db.commit()

    log_config_audit(
        db=db,
        config_type="THRESHOLD",
        item_id=thresh.id,
        changed_by=current_user.id,
        old_value=old_val,
        new_value=req.dict(),
        change_reason=f"Clinician updated {req.vital_type} thresholds"
    )

    return {"message": "Vitals threshold configured successfully"}
