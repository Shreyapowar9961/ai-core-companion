from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, UserRole, require_roles, verify_patient_access
from app.core.audit import log_audit_event, log_config_audit
from app.models.patient import Patient
from app.models.monitoring import MonitoringPlan, CheckinTask, CommunicationLog, PatientFeedback
from app.services.monitoring_scheduler import BackgroundMonitoringScheduler

router = APIRouter(prefix="/monitoring", tags=["Automated Patient Monitoring"])

class MonitoringPlanCreateRequest(BaseModel):
    patient_id: str
    start_date: date = date.today()
    end_date: date
    frequency: str = "DAILY" # DAILY, TWICE_DAILY, WEEKLY
    timezone: str = "Asia/Kolkata"
    approved_questions: List[str] = [
        "pain_level",
        "breathlessness",
        "dizziness",
        "swelling",
        "wound_status",
        "vitals_bp",
        "vitals_spo2"
    ]
    communication_channel: str = "VOICE" # VOICE, WHATSAPP, SMS
    is_active: bool = True

@router.post("/plans")
def create_or_update_monitoring_plan(
    req: MonitoringPlanCreateRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    """
    Phase 3: Doctor configures monitoring plan for an assigned patient.
    """
    patient = db.get(Patient, req.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    verify_patient_access(req.patient_id, current_user, patient.facility_id)

    plan = db.execute(
        select(MonitoringPlan).where(MonitoringPlan.patient_id == req.patient_id)
    ).scalars().first()

    if not plan:
        plan = MonitoringPlan(
            patient_id=req.patient_id,
            clinician_id=current_user.id,
            start_date=req.start_date,
            end_date=req.end_date,
            frequency=req.frequency,
            timezone=req.timezone,
            approved_questions=req.approved_questions,
            communication_channel=req.communication_channel,
            is_active=req.is_active
        )
        db.add(plan)
    else:
        plan.start_date = req.start_date
        plan.end_date = req.end_date
        plan.frequency = req.frequency
        plan.timezone = req.timezone
        plan.approved_questions = req.approved_questions
        plan.communication_channel = req.communication_channel
        plan.is_active = req.is_active
        plan.clinician_id = current_user.id

    db.commit()
    db.refresh(plan)

    log_config_audit(
        db=db,
        config_type="SCHEDULE",
        item_id=plan.id,
        changed_by=current_user.id,
        new_value={
            "patient_id": req.patient_id,
            "frequency": req.frequency,
            "channel": req.communication_channel,
            "end_date": str(req.end_date)
        },
        change_reason="Monitoring plan configuration updated"
    )

    return {
        "id": plan.id,
        "patient_id": plan.patient_id,
        "frequency": plan.frequency,
        "communication_channel": plan.communication_channel,
        "approved_questions": plan.approved_questions,
        "start_date": plan.start_date.isoformat(),
        "end_date": plan.end_date.isoformat(),
        "is_active": plan.is_active,
        "status": "CONFIGURED"
    }

@router.get("/plans/patient/{patient_id}")
def get_monitoring_plan(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    plan = db.execute(
        select(MonitoringPlan).where(MonitoringPlan.patient_id == patient_id)
    ).scalars().first()

    if not plan:
        # Return default plan values
        return {
            "has_plan": False,
            "patient_id": patient_id,
            "frequency": "DAILY",
            "communication_channel": "VOICE",
            "approved_questions": ["pain_level", "breathlessness", "dizziness", "wound_status", "vitals_spo2"],
            "start_date": date.today().isoformat(),
            "end_date": (date.today() + timedelta(days=30)).isoformat(),
            "is_active": True
        }

    return {
        "has_plan": True,
        "id": plan.id,
        "patient_id": plan.patient_id,
        "frequency": plan.frequency,
        "communication_channel": plan.communication_channel,
        "approved_questions": plan.approved_questions,
        "start_date": plan.start_date.isoformat(),
        "end_date": plan.end_date.isoformat(),
        "is_active": plan.is_active
    }

@router.get("/tasks/patient/{patient_id}")
def get_monitoring_tasks(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    tasks = db.execute(
        select(CheckinTask).where(CheckinTask.patient_id == patient_id)
        .order_by(desc(CheckinTask.scheduled_for)).limit(30)
    ).scalars().all()

    return [
        {
            "id": t.id,
            "scheduled_for": t.scheduled_for.isoformat(),
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "status": t.status,
            "channel": t.channel,
            "category": t.category, # ROUTINE, FOLLOW_UP_REQUIRED, NEEDS_CLINICIAN_REVIEW, UNANSWERED
            "category_reason": t.category_reason,
            "alert_id": t.alert_id,
            "response": t.response_json
        }
        for t in tasks
    ]

@router.post("/scheduler/trigger")
def trigger_scheduler_cycle(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    """
    On-demand trigger for testing and verifying the automated monitoring scheduler.
    """
    result = BackgroundMonitoringScheduler.run_cycle(db)
    return {"message": "Monitoring scheduler cycle completed.", "result": result}

@router.get("/communications/patient/{patient_id}")
def get_communications_for_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    comms = db.execute(
        select(CommunicationLog).where(CommunicationLog.patient_id == patient_id)
        .order_by(desc(CommunicationLog.sent_at)).limit(50)
    ).scalars().all()

    return [
        {
            "id": c.id,
            "channel": c.channel,
            "message_type": c.message_type,
            "recipient_phone": c.recipient_phone,
            "content": c.content,
            "status": c.status,
            "is_simulated": c.is_simulated,
            "sent_at": c.sent_at.isoformat()
        }
        for c in comms
    ]

@router.get("/feedback/patient/{patient_id}")
def get_feedback_for_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    fbs = db.execute(
        select(PatientFeedback).where(PatientFeedback.patient_id == patient_id)
        .order_by(desc(PatientFeedback.created_at))
    ).scalars().all()

    return [
        {
            "id": f.id,
            "rating": f.rating,
            "category": f.category,
            "comments": f.comments,
            "created_at": f.created_at.isoformat()
        }
        for f in fbs
    ]
