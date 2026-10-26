from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, verify_patient_access
from app.models.clinical import SymptomCheckin
from app.models.patient import Patient
from app.schemas.clinical import SymptomCheckinCreate, SymptomCheckinResponse
from app.services.rules_engine import RulesEngine
from app.core.audit import log_audit_event

router = APIRouter(prefix="/checkins", tags=["Daily Symptom Check-in"])

@router.post("/patient/{patient_id}", response_model=SymptomCheckinResponse, status_code=status.HTTP_201_CREATED)
def submit_symptom_checkin(
    patient_id: str,
    req: SymptomCheckinCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    verify_patient_access(patient_id, current_user, patient.facility_id, db=db)

    comparison = dict(req.comparison_with_yesterday)
    prev_stmt = select(SymptomCheckin).where(
        SymptomCheckin.patient_id == patient_id
    ).order_by(desc(SymptomCheckin.recorded_at)).limit(1)
    prev_checkin = db.execute(prev_stmt).scalars().first()

    if prev_checkin and not comparison:
        if req.pain_level > prev_checkin.pain_level:
            comparison["pain"] = "worsened"
        elif req.pain_level < prev_checkin.pain_level:
            comparison["pain"] = "improved"
        else:
            comparison["pain"] = "unchanged"

    checkin = SymptomCheckin(
        patient_id=patient_id,
        call_session_id=req.call_session_id,
        checkin_type=req.checkin_type,
        pain_level=req.pain_level,
        weakness=req.weakness,
        dizziness=req.dizziness,
        breathlessness=req.breathlessness,
        swelling=req.swelling,
        fever=req.fever,
        wound_status=req.wound_status,
        appetite=req.appetite,
        sleep_quality=req.sleep_quality,
        other_symptoms_verbatim=req.other_symptoms_verbatim,
        other_symptoms_structured=req.other_symptoms_structured,
        comparison_with_yesterday=comparison,
        recorded_at=datetime.utcnow()
    )
    db.add(checkin)
    db.flush()

    RulesEngine.evaluate_symptom_checkin(db, patient_id, checkin)
    db.commit()
    db.refresh(checkin)

    log_audit_event(
        db=db,
        event_type="SYMPTOM_CHECKIN_SUBMITTED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="symptom_checkin",
        details={"checkin_id": checkin.id, "pain_level": checkin.pain_level},
        patient_id=patient_id
    )

    return checkin

@router.get("/patient/{patient_id}", response_model=List[SymptomCheckinResponse])
@router.get("/history/{patient_id}", response_model=List[SymptomCheckinResponse])
@router.get("/patient/{patient_id}/history", response_model=List[SymptomCheckinResponse])
def list_patient_checkins(
    patient_id: str,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    verify_patient_access(patient_id, current_user, patient.facility_id, db=db)

    stmt = select(SymptomCheckin).where(
        SymptomCheckin.patient_id == patient_id
    ).order_by(desc(SymptomCheckin.recorded_at)).limit(limit)

    results = db.execute(stmt).scalars().all()
    return results
