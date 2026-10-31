from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, UserRole, require_roles
from app.core.audit import log_audit_event
from app.models.patient import Patient, CarePlan, Caregiver
from app.models.clinical import MedicationSchedule, MedicationLog, SymptomCheckin, VitalReading
from app.models.monitoring import MonitoringPlan, CheckinTask, CommunicationLog, PatientFeedback
from app.models.rules_alert import Alert
from app.models.progress import DailyProgressScore
from app.services.rules_engine import RulesEngine

router = APIRouter(prefix="/portal", tags=["Patient Portal"])

def get_verified_patient_id(current_user: AuthUser, db: Session) -> str:
    """
    Strict server-side patient-to-account verification (Phase 2 & 9).
    Never trusts client-supplied patient_id.
    """
    if current_user.role == UserRole.PATIENT:
        if not current_user.patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: No verified patient record linked to this account."
            )
        return current_user.patient_id

    if current_user.role == UserRole.ADMIN:
        # Admin testing mode: return first active patient if no explicit id
        patient = db.execute(select(Patient).where(Patient.status == "ACTIVE")).scalars().first()
        if patient:
            return patient.id
        raise HTTPException(status_code=404, detail="No active patient found for preview.")

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Patient portal is reserved for registered patients."
    )

# ----------------- Request Schemas -----------------

class ConfirmMedicationRequest(BaseModel):
    medication_schedule_id: Optional[str] = None
    medicine_name: str
    dosage: Optional[str] = None
    scheduled_time: Optional[datetime] = None

class ReportMissedMedicationRequest(BaseModel):
    medication_schedule_id: Optional[str] = None
    medicine_name: str
    dosage: Optional[str] = None
    stated_reason: str
    scheduled_time: Optional[datetime] = None

class SubmitCheckinRequest(BaseModel):
    task_id: Optional[str] = None
    pain_level: int = 0 # 0-10
    breathlessness: str = "none" # none, mild, moderate, severe
    dizziness: str = "none"
    swelling: str = "none"
    wound_status: str = "healing_well" # healing_well, redness, discharge, pain
    appetite: str = "normal"
    sleep_quality: str = "good"
    other_notes: Optional[str] = None
    # Optional vitals provided during check-in
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None
    spo2: Optional[float] = None
    heart_rate: Optional[float] = None
    temperature_f: Optional[float] = None
    weight_kg: Optional[float] = None

class FeedbackSubmissionRequest(BaseModel):
    checkin_task_id: Optional[str] = None
    rating: int # 1 to 5
    category: str = "GENERAL_RECOVERY"
    comments: Optional[str] = None

class UpdateLanguageRequest(BaseModel):
    language: str # 'en', 'hi', 'mr'

# ----------------- Endpoints -----------------

@router.get("/profile")
def get_patient_profile(
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found.")

    care_plan = db.execute(
        select(CarePlan).where(CarePlan.patient_id == patient_id, CarePlan.is_active == True)
    ).scalars().first()

    return {
        "id": patient.id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "name": f"{patient.first_name} {patient.last_name}",
        "dob": patient.dob.isoformat(),
        "gender": patient.gender,
        "phone": patient.phone,
        "email": patient.email,
        "diagnosis": patient.diagnosis,
        "discharge_date": patient.discharge_date.isoformat(),
        "programme_duration_days": patient.programme_duration_days,
        "preferred_language": patient.preferred_language,
        "status": patient.status,
        "call_window": f"{patient.call_window_start} - {patient.call_window_end}",
        "treating_doctor_name": patient.treating_doctor_name,
        "treating_doctor_phone": patient.treating_doctor_phone,
        "treating_doctor_specialty": patient.treating_doctor_specialty,
        "care_plan": {
            "diet": care_plan.diet_instructions if care_plan else None,
            "hydration_target_glasses": care_plan.hydration_target_glasses if care_plan else 8,
            "activity_target_minutes": care_plan.activity_target_minutes if care_plan else 20,
            "physiotherapy": care_plan.physiotherapy_instructions if care_plan else None
        } if care_plan else None
    }

@router.get("/dashboard")
def get_patient_dashboard(
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found.")

    # 1. Today's medication stats
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_logs = db.execute(
        select(MedicationLog).where(
            MedicationLog.patient_id == patient_id,
            MedicationLog.scheduled_time >= today_start
        )
    ).scalars().all()

    taken_count = sum(1 for m in today_logs if m.status == "TAKEN")
    missed_count = sum(1 for m in today_logs if m.status in ["MISSED", "DEFERRED"])

    # Prescribed active medications
    schedules = db.execute(
        select(MedicationSchedule).where(
            MedicationSchedule.patient_id == patient_id,
            MedicationSchedule.is_active == True
        )
    ).scalars().all()

    total_today_scheduled = len(schedules)
    pending_count = max(0, total_today_scheduled - (taken_count + missed_count))

    # 2. Latest Progress Score
    progress_score = db.execute(
        select(DailyProgressScore).where(DailyProgressScore.patient_id == patient_id)
        .order_by(desc(DailyProgressScore.score_date)).limit(1)
    ).scalars().first()

    # 3. Next upcoming or pending checkin
    next_task = db.execute(
        select(CheckinTask).where(
            CheckinTask.patient_id == patient_id,
            CheckinTask.status == "PENDING"
        ).order_by(CheckinTask.scheduled_for).limit(1)
    ).scalars().first()

    # 4. Recent notification count
    notif_count = len(db.execute(
        select(CommunicationLog).where(CommunicationLog.patient_id == patient_id)
    ).scalars().all())

    return {
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "diagnosis": patient.diagnosis,
        "preferred_language": patient.preferred_language,
        "recovery_status": patient.status,
        "days_since_discharge": (date.today() - patient.discharge_date).days,
        "progress_score": progress_score.overall_score if progress_score else 92.0,
        "medication_summary": {
            "total": total_today_scheduled,
            "taken": taken_count,
            "missed": missed_count,
            "pending": pending_count,
            "adherence_rate": round((taken_count / total_today_scheduled * 100), 1) if total_today_scheduled > 0 else 100.0
        },
        "next_checkin": {
            "id": next_task.id if next_task else None,
            "scheduled_for": next_task.scheduled_for.isoformat() if next_task else (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "channel": next_task.channel if next_task else "PORTAL",
            "is_due": True if next_task and next_task.scheduled_for <= datetime.utcnow() else False
        },
        "doctor": {
            "name": patient.treating_doctor_name or "Attending Cardiologist",
            "phone": patient.treating_doctor_phone or "+91 20 2612 3456"
        },
        "total_notifications": notif_count
    }

@router.get("/checkins/upcoming")
def get_upcoming_checkins(
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
    tasks = db.execute(
        select(CheckinTask).where(
            CheckinTask.patient_id == patient_id,
            CheckinTask.status.in_(["PENDING", "ACTIVE"])
        ).order_by(CheckinTask.scheduled_for)
    ).scalars().all()

    return [
        {
            "id": t.id,
            "scheduled_for": t.scheduled_for.isoformat(),
            "status": t.status,
            "channel": t.channel,
            "category": t.category,
            "is_due": t.scheduled_for <= datetime.utcnow()
        }
        for t in tasks
    ]

@router.get("/checkins/history")
def get_checkin_history(
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
    symptoms = db.execute(
        select(SymptomCheckin).where(SymptomCheckin.patient_id == patient_id)
        .order_by(desc(SymptomCheckin.recorded_at)).limit(20)
    ).scalars().all()

    return [
        {
            "id": s.id,
            "recorded_at": s.recorded_at.isoformat(),
            "checkin_type": s.checkin_type,
            "pain_level": s.pain_level,
            "breathlessness": s.breathlessness,
            "dizziness": s.dizziness,
            "swelling": s.swelling,
            "fever": s.fever,
            "wound_status": s.wound_status,
            "notes": s.other_symptoms_verbatim
        }
        for s in symptoms
    ]

@router.post("/checkins/submit")
def submit_checkin_response(
    req: SubmitCheckinRequest,
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Submits patient recovery checkin responses, applies biological plausibility,
    evaluates rules via RulesEngine, categorises the checkin, and creates automated alerts if needed.
    """
    patient_id = get_verified_patient_id(current_user, db)
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    # 1. Save SymptomCheckin
    checkin = SymptomCheckin(
        patient_id=patient_id,
        checkin_type="PORTAL_DAILY",
        recorded_at=datetime.utcnow(),
        pain_level=req.pain_level,
        breathlessness=req.breathlessness,
        dizziness=req.dizziness,
        swelling=req.swelling,
        wound_status=req.wound_status,
        appetite=req.appetite,
        sleep_quality=req.sleep_quality,
        other_symptoms_verbatim=req.other_notes
    )
    db.add(checkin)
    db.flush()

    # 2. Record Vitals if provided with Plausibility checks
    vitals_recorded = []
    if req.spo2 is not None:
        is_plausible = RulesEngine.validate_vital_plausibility("SPO2", req.spo2)
        v = VitalReading(
            patient_id=patient_id,
            vital_type="SPO2",
            value=req.spo2,
            unit="%",
            status="NORMAL" if is_plausible and req.spo2 >= 92 else ("CRITICAL" if req.spo2 < 88 else "WARNING"),
            voice_confirmed=True,
            notes="Patient portal self-reported"
        )
        db.add(v)
        vitals_recorded.append(v)

    if req.systolic_bp is not None:
        is_plausible = RulesEngine.validate_vital_plausibility("BP_SYSTOLIC", req.systolic_bp)
        v = VitalReading(
            patient_id=patient_id,
            vital_type="BP_SYSTOLIC",
            value=req.systolic_bp,
            secondary_value=req.diastolic_bp,
            unit="mmHg",
            status="NORMAL" if is_plausible and req.systolic_bp <= 140 else "WARNING",
            voice_confirmed=True,
            notes="Patient portal self-reported"
        )
        db.add(v)
        vitals_recorded.append(v)

    if req.heart_rate is not None:
        is_plausible = RulesEngine.validate_vital_plausibility("PULSE", req.heart_rate)
        v = VitalReading(
            patient_id=patient_id,
            vital_type="PULSE",
            value=req.heart_rate,
            unit="bpm",
            status="NORMAL" if is_plausible and 55 <= req.heart_rate <= 100 else "WARNING",
            voice_confirmed=True,
            notes="Patient portal self-reported"
        )
        db.add(v)
        vitals_recorded.append(v)

    db.flush()

    # 3. Categorise response & Evaluate Rules
    category = "ROUTINE"
    reasons = []

    # Clinical Red Flags
    if req.pain_level >= 8:
        category = "NEEDS_CLINICIAN_REVIEW"
        reasons.append(f"Severe pain score: {req.pain_level}/10")
    elif req.pain_level >= 5:
        category = "FOLLOW_UP_REQUIRED"
        reasons.append(f"Moderate pain score: {req.pain_level}/10")

    if req.breathlessness in ["severe", "moderate"]:
        category = "NEEDS_CLINICIAN_REVIEW"
        reasons.append(f"Acute breathlessness reported ({req.breathlessness})")

    if req.wound_status in ["discharge", "redness"]:
        category = "NEEDS_CLINICIAN_REVIEW"
        reasons.append(f"Surgical wound complication ({req.wound_status})")

    if req.spo2 is not None and req.spo2 < 90:
        category = "NEEDS_CLINICIAN_REVIEW"
        reasons.append(f"Hypoxia reading: SpO2 {req.spo2}%")

    if not reasons:
        category = "ROUTINE"
        reasons.append("All reported parameters within safe expected post-operative bounds.")

    category_reason_str = "; ".join(reasons)

    # 4. Trigger alert in database if clinical review needed
    created_alert_id = None
    if category == "NEEDS_CLINICIAN_REVIEW":
        alert = Alert(
            patient_id=patient_id,
            rule_code="PORTAL_CHECKIN_REVIEW",
            severity="CRITICAL" if (req.spo2 and req.spo2 < 88) or req.breathlessness == "severe" else "HIGH",
            title=f"Check-in Alert: {reasons[0]}",
            description=f"Patient {patient.first_name} {patient.last_name} submitted check-in requiring review. Details: {category_reason_str}",
            supporting_data={
                "pain_level": req.pain_level,
                "breathlessness": req.breathlessness,
                "wound_status": req.wound_status,
                "spo2": req.spo2,
                "bp": f"{req.systolic_bp}/{req.diastolic_bp}" if req.systolic_bp else None
            },
            status="OPEN",
            sla_due_at=datetime.utcnow() + timedelta(minutes=15 if req.spo2 and req.spo2 < 88 else 60)
        )
        db.add(alert)
        db.flush()
        created_alert_id = alert.id

    # 5. Complete CheckinTask if task_id provided or create completed task record
    if req.task_id:
        task = db.get(CheckinTask, req.task_id)
        if task and task.patient_id == patient_id:
            task.status = "COMPLETED"
            task.completed_at = datetime.utcnow()
            task.category = category
            task.category_reason = category_reason_str
            task.alert_id = created_alert_id
            task.response_json = {
                "pain": req.pain_level,
                "breathlessness": req.breathlessness,
                "dizziness": req.dizziness,
                "wound": req.wound_status,
                "vitals": {"spo2": req.spo2, "bp": req.systolic_bp}
            }
    else:
        task = CheckinTask(
            patient_id=patient_id,
            scheduled_for=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            status="COMPLETED",
            channel="PORTAL",
            category=category,
            category_reason=category_reason_str,
            alert_id=created_alert_id,
            response_json={
                "pain": req.pain_level,
                "breathlessness": req.breathlessness,
                "wound": req.wound_status
            }
        )
        db.add(task)

    # 6. Create simulated feedback communication prompt
    feedback_log = CommunicationLog(
        patient_id=patient_id,
        channel="SIMULATED_SMS",
        message_type="FEEDBACK_REQUEST",
        recipient_phone=patient.phone,
        content=f"Thank you for submitting your recovery check-in. How would you rate your recovery support today? Open portal to provide 1-click feedback.",
        status="DELIVERED",
        is_simulated=True
    )
    db.add(feedback_log)

    db.commit()

    log_audit_event(
        db=db,
        event_type="PATIENT_CHECKIN_SUBMITTED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="symptom_checkin",
        details={"category": category, "reasons": reasons, "alert_id": created_alert_id},
        patient_id=patient_id
    )

    return {
        "message": "Recovery check-in submitted successfully.",
        "category": category,
        "category_reason": category_reason_str,
        "alert_generated": created_alert_id is not None,
        "status": "COMPLETED"
    }

@router.get("/medications/schedule")
def get_medication_schedule(
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
    schedules = db.execute(
        select(MedicationSchedule).where(
            MedicationSchedule.patient_id == patient_id,
            MedicationSchedule.is_active == True
        )
    ).scalars().all()

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_logs = db.execute(
        select(MedicationLog).where(
            MedicationLog.patient_id == patient_id,
            MedicationLog.scheduled_time >= today_start
        )
    ).scalars().all()

    # Map today's status per medicine
    status_map = {}
    for l in today_logs:
        status_map[l.medicine_name.lower()] = {
            "status": l.status,
            "actual_time": l.actual_time.isoformat() if l.actual_time else None,
            "reason": l.stated_reason
        }

    result = []
    for s in schedules:
        st = status_map.get(s.medicine_name.lower(), {"status": "PENDING", "actual_time": None, "reason": None})
        result.append({
            "id": s.id,
            "medicine_name": s.medicine_name,
            "dosage": s.dosage,
            "frequency": s.frequency,
            "dose_times": s.dose_times or ["09:00"],
            "instructions": s.instructions or "Take with a glass of water after food",
            "route": s.route or "Oral",
            "status": st["status"],
            "confirmed_at": st["actual_time"],
            "reason": st["reason"]
        })

    return result

@router.get("/medications/history")
def get_medication_history(
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
    logs = db.execute(
        select(MedicationLog).where(MedicationLog.patient_id == patient_id)
        .order_by(desc(MedicationLog.scheduled_time)).limit(30)
    ).scalars().all()

    return [
        {
            "id": l.id,
            "medicine_name": l.medicine_name,
            "dosage": l.dosage,
            "scheduled_time": l.scheduled_time.isoformat(),
            "actual_time": l.actual_time.isoformat() if l.actual_time else None,
            "status": l.status,
            "stated_reason": l.stated_reason,
            "recorded_via": l.recorded_via
        }
        for l in logs
    ]

@router.post("/medications/confirm-taken")
def confirm_medication_taken(
    req: ConfirmMedicationRequest,
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Patient confirms medication intake. Recorded as patient-reported event (MD-01, Phase 4).
    """
    patient_id = get_verified_patient_id(current_user, db)

    log_entry = MedicationLog(
        patient_id=patient_id,
        medication_schedule_id=req.medication_schedule_id,
        medicine_name=req.medicine_name,
        dosage=req.dosage or "Prescribed dose",
        scheduled_time=req.scheduled_time or datetime.utcnow(),
        actual_time=datetime.utcnow(),
        status="TAKEN",
        stated_reason="Patient confirmed via portal",
        recorded_via="PATIENT_PORTAL"
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    log_audit_event(
        db=db,
        event_type="PATIENT_CONFIRMED_MEDICATION",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="medication_log",
        details={"medicine_name": req.medicine_name, "status": "TAKEN"},
        patient_id=patient_id
    )

    return {
        "message": f"Dose of {req.medicine_name} recorded as taken.",
        "status": "TAKEN",
        "confirmed_at": log_entry.actual_time.isoformat()
    }

@router.post("/medications/report-missed")
def report_missed_medication(
    req: ReportMissedMedicationRequest,
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Patient reports missed dose with structured reason (MD-02, Phase 4).
    """
    patient_id = get_verified_patient_id(current_user, db)

    log_entry = MedicationLog(
        patient_id=patient_id,
        medication_schedule_id=req.medication_schedule_id,
        medicine_name=req.medicine_name,
        dosage=req.dosage or "Prescribed dose",
        scheduled_time=req.scheduled_time or datetime.utcnow(),
        actual_time=datetime.utcnow(),
        status="MISSED",
        stated_reason=req.stated_reason,
        recorded_via="PATIENT_PORTAL"
    )
    db.add(log_entry)
    db.flush()

    # Evaluate consecutive misses in RulesEngine
    RulesEngine.evaluate_medication_miss(db, patient_id, req.medicine_name)

    db.commit()
    db.refresh(log_entry)

    log_audit_event(
        db=db,
        event_type="PATIENT_REPORTED_MISSED_MEDICATION",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="medication_log",
        details={"medicine_name": req.medicine_name, "reason": req.stated_reason},
        patient_id=patient_id
    )

    return {
        "message": f"Missed dose for {req.medicine_name} logged.",
        "status": "MISSED",
        "reason": req.stated_reason
    }

@router.get("/notifications")
def get_patient_notifications(
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
    logs = db.execute(
        select(CommunicationLog).where(CommunicationLog.patient_id == patient_id)
        .order_by(desc(CommunicationLog.sent_at)).limit(25)
    ).scalars().all()

    return [
        {
            "id": l.id,
            "channel": l.channel,
            "message_type": l.message_type,
            "content": l.content,
            "status": l.status,
            "is_simulated": l.is_simulated,
            "sent_at": l.sent_at.isoformat()
        }
        for l in logs
    ]

@router.get("/communications")
def get_communication_history(
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
    logs = db.execute(
        select(CommunicationLog).where(CommunicationLog.patient_id == patient_id)
        .order_by(desc(CommunicationLog.sent_at)).limit(50)
    ).scalars().all()

    return [
        {
            "id": l.id,
            "channel": l.channel, # SIMULATED_VOICE, SIMULATED_WHATSAPP, SIMULATED_SMS
            "message_type": l.message_type,
            "content": l.content,
            "status": l.status,
            "is_simulated": True,
            "sent_at": l.sent_at.isoformat()
        }
        for l in logs
    ]

@router.post("/feedback")
def submit_patient_feedback(
    req: FeedbackSubmissionRequest,
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5.")

    fb = PatientFeedback(
        patient_id=patient_id,
        checkin_task_id=req.checkin_task_id,
        rating=req.rating,
        category=req.category,
        comments=req.comments,
        created_at=datetime.utcnow()
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    log_audit_event(
        db=db,
        event_type="PATIENT_FEEDBACK_SUBMITTED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="patient_feedback",
        details={"rating": req.rating, "category": req.category},
        patient_id=patient_id
    )

    return {"message": "Thank you for your feedback!", "id": fb.id, "status": "RECEIVED"}

@router.get("/feedback")
def list_patient_feedback(
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
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

@router.put("/language")
def update_patient_language(
    req: UpdateLanguageRequest,
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
    if req.language not in ["en", "hi", "mr"]:
        raise HTTPException(status_code=400, detail="Language must be one of: 'en', 'hi', 'mr'.")

    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    patient.preferred_language = req.language
    db.commit()

    return {"message": f"Preferred language updated to '{req.language}'.", "language": req.language}
