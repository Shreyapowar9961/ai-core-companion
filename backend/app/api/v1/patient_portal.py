from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, and_, func
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, UserRole, require_roles
from app.core.audit import log_audit_event
from app.models.patient import Patient, CarePlan, Caregiver
from app.models.clinical import MedicationSchedule, MedicationLog, SymptomCheckin, VitalReading
from app.models.monitoring import MonitoringPlan, CheckinTask, CommunicationLog, PatientFeedback
from app.models.prescription import PrescriptionUpload
from app.models.rules_alert import Alert
from app.models.progress import DailyProgressScore
from app.models.device_token import PushDeviceRegistration
from app.schemas.device_token import (
    DeviceTokenRegisterRequest,
    DeviceTokenUnregisterRequest,
    NotificationPreferencesUpdateRequest,
    NotificationPreferencesResponse
)
from app.services.fcm_service import mask_token
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

    # 2. Latest Progress Score (calculate real-time from database)
    from app.services.progress_service import ProgressService
    progress_score = ProgressService.calculate_daily_progress_score(db, patient_id)

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
        "progress_score": progress_score.overall_score if progress_score else 100.0,
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
            "name": patient.treating_doctor_name or "Attending Clinician",
            "phone": patient.treating_doctor_phone or ""
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

    # 4. Trigger alert in database if clinical review needed (deduplicated)
    created_alert_id = None
    if category == "NEEDS_CLINICIAN_REVIEW":
        alert, created = RulesEngine.create_or_get_alert(
            db=db,
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
            sla_due_at=datetime.utcnow() + timedelta(minutes=15 if req.spo2 and req.spo2 < 88 else 60),
            action_log_notes="Auto-triggered by patient portal check-in review submission."
        )
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

@router.get("/prescriptions")
def get_patient_prescriptions(
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Returns official uploaded prescriptions and doctor verification status for the logged-in patient.
    """
    patient_id = get_verified_patient_id(current_user, db)
    prescriptions = db.execute(
        select(PrescriptionUpload).where(PrescriptionUpload.patient_id == patient_id)
        .order_by(desc(PrescriptionUpload.created_at))
    ).scalars().all()

    return [
        {
            "id": p.id,
            "filename": p.filename,
            "status": p.status,
            "verified_by": p.verified_by,
            "verified_at": p.verified_at.isoformat() if p.verified_at else None,
            "created_at": p.created_at.isoformat(),
            "medications": p.verified_medications or p.extracted_medications or [],
            "clinician_notes": p.clinician_notes
        }
        for p in prescriptions
    ]

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

def resolve_intended_dose(
    db: Session,
    patient_id: str,
    medicine_name: str,
    medication_schedule_id: Optional[str],
    scheduled_time: Optional[datetime],
) -> Tuple[datetime, Optional[MedicationLog], Optional[MedicationSchedule]]:
    """
    Phase 1.3: Resolves unambiguous dose occurrence and matches existing medication log.
    - Inspects active schedule to find expected dose occurrences.
    - If multiple dose occurrences match without an explicit scheduled_time, safely rejects (HTTP 409).
    - If multiple existing logs match without unambiguous resolution, safely rejects (HTTP 409).
    - Does NOT substitute the latest-created medication log arbitrarily.
    - Retains full compatibility with single-dose / explicit confirmations.
    """
    sched: Optional[MedicationSchedule] = None
    if medication_schedule_id:
        sched = db.get(MedicationSchedule, medication_schedule_id)
        if sched and sched.patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Medication schedule does not belong to verified patient."
            )
    else:
        # Search for active schedule matching patient and medicine name
        sched_stmt = select(MedicationSchedule).where(
            MedicationSchedule.patient_id == patient_id,
            MedicationSchedule.is_active == True
        )
        candidates = db.execute(sched_stmt).scalars().all()
        matched_scheds = [
            s for s in candidates
            if s.patient_id == patient_id and s.medicine_name.strip().lower() == medicine_name.strip().lower()
        ]
        sched = matched_scheds[0] if matched_scheds else None

    ref_time = scheduled_time or datetime.utcnow()
    explicit_time = (scheduled_time is not None)
    target_sched_time = ref_time

    if sched:
        from app.api.v1.dashboard import parse_schedule_dose_times
        dose_times = parse_schedule_dose_times(sched)
        if dose_times:
            ref_date = ref_time.date()
            candidate_slots: List[Tuple[datetime, float]] = []
            for d in [ref_date - timedelta(days=1), ref_date, ref_date + timedelta(days=1)]:
                for t in dose_times:
                    slot_dt = datetime.combine(d, t)
                    diff = abs((slot_dt - ref_time).total_seconds())
                    if diff <= 2 * 3600:
                        candidate_slots.append((slot_dt, diff))

            if candidate_slots:
                if explicit_time:
                    exact_matches = [s for s, diff in candidate_slots if s == scheduled_time or diff < 60]
                    if exact_matches:
                        target_sched_time = exact_matches[0]
                    else:
                        candidate_slots.sort(key=lambda x: x[1])
                        if len(candidate_slots) > 1 and abs(candidate_slots[0][1] - candidate_slots[1][1]) < 300:
                            raise HTTPException(
                                status_code=status.HTTP_409_CONFLICT,
                                detail=f"Ambiguous dose matching: Scheduled time {scheduled_time.isoformat()} matches multiple dose occurrences equally. Please specify the exact scheduled dose occurrence time."
                            )
                        target_sched_time = candidate_slots[0][0]
                else:
                    if len(candidate_slots) > 1:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=f"Ambiguous dose confirmation: Multiple scheduled dose occurrences match the current window for {medicine_name}. Please specify an explicit scheduled_time."
                        )
                    else:
                        target_sched_time = candidate_slots[0][0]

    time_min = target_sched_time - timedelta(hours=2)
    time_max = target_sched_time + timedelta(hours=2)

    existing_stmt = select(MedicationLog).where(
        MedicationLog.patient_id == patient_id
    )
    if sched:
        existing_stmt = existing_stmt.where(MedicationLog.medication_schedule_id == sched.id)
    elif medication_schedule_id:
        existing_stmt = existing_stmt.where(MedicationLog.medication_schedule_id == medication_schedule_id)
    else:
        existing_stmt = existing_stmt.where(MedicationLog.medicine_name == medicine_name)

    existing_stmt = existing_stmt.where(
        MedicationLog.scheduled_time >= time_min,
        MedicationLog.scheduled_time <= time_max
    )

    all_logs = db.execute(existing_stmt).scalars().all()
    matching_logs = [
        l for l in all_logs
        if l.patient_id == patient_id
        and (l.medication_schedule_id == sched.id if sched else (l.medication_schedule_id == medication_schedule_id if medication_schedule_id else l.medicine_name.strip().lower() == medicine_name.strip().lower()))
        and (time_min <= l.scheduled_time <= time_max)
    ]

    matched_log: Optional[MedicationLog] = None
    if len(matching_logs) == 1:
        matched_log = matching_logs[0]
    elif len(matching_logs) > 1:
        exact_logs = [l for l in matching_logs if l.scheduled_time == target_sched_time]
        if len(exact_logs) == 1:
            matched_log = exact_logs[0]
        elif len(exact_logs) > 1:
            taken_logs = [l for l in exact_logs if l.status == "TAKEN"]
            matched_log = taken_logs[0] if taken_logs else exact_logs[0]
        else:
            sorted_logs = sorted(matching_logs, key=lambda l: abs((l.scheduled_time - target_sched_time).total_seconds()))
            diff1 = abs((sorted_logs[0].scheduled_time - target_sched_time).total_seconds())
            diff2 = abs((sorted_logs[1].scheduled_time - target_sched_time).total_seconds())
            if (diff2 - diff1) < 1800:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ambiguous dose matching: Multiple existing medication logs match the window around {target_sched_time.isoformat()}. Please specify an exact scheduled_time."
                )
            matched_log = sorted_logs[0]

    return target_sched_time, matched_log, sched


@router.post("/medications/confirm-taken")
def confirm_medication_taken(
    req: ConfirmMedicationRequest,
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Phase 1.3: Idempotent patient confirmation of medication intake.
    - Prevents ambiguous dose matching when multiple candidate occurrences exist.
    - Repeated confirmation of the same dose does NOT create duplicate TAKEN rows.
    - Allows correcting a mistaken MISSED log to TAKEN in-place.
    """
    patient_id = get_verified_patient_id(current_user, db)

    # Resolve intended dose occurrence and match existing log
    target_sched_time, existing_log, sched = resolve_intended_dose(
        db=db,
        patient_id=patient_id,
        medicine_name=req.medicine_name,
        medication_schedule_id=req.medication_schedule_id,
        scheduled_time=req.scheduled_time
    )

    if existing_log:
        if existing_log.status == "TAKEN":
            # Already confirmed taken: idempotent no-op, return existing log
            return {
                "message": f"Dose of {req.medicine_name} already confirmed as taken.",
                "status": "TAKEN",
                "confirmed_at": (existing_log.actual_time or existing_log.created_at).isoformat(),
                "idempotent": True
            }
        else:
            # Update pending/missed log to taken (remedy mistaken miss)
            existing_log.status = "TAKEN"
            existing_log.actual_time = datetime.utcnow()
            existing_log.stated_reason = "Patient confirmed via portal"
            existing_log.recorded_via = "PATIENT_PORTAL"
            db.commit()
            db.refresh(existing_log)
            log_entry = existing_log
    else:
        log_entry = MedicationLog(
            patient_id=patient_id,
            medication_schedule_id=req.medication_schedule_id or (sched.id if sched else None),
            medicine_name=req.medicine_name,
            dosage=req.dosage or (sched.dosage if sched else "Prescribed dose"),
            scheduled_time=target_sched_time,
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
        details={"medicine_name": req.medicine_name, "status": "TAKEN", "log_id": log_entry.id, "scheduled_time": target_sched_time.isoformat()},
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
    Phase 1.3: Idempotent reporting of missed medication dose.
    - Prevents overwriting a TAKEN dose to MISSED (raises HTTP 409 Conflict).
    - Prevents ambiguous dose matching when multiple candidate occurrences exist.
    """
    patient_id = get_verified_patient_id(current_user, db)

    # Resolve intended dose occurrence and match existing log
    target_sched_time, existing_log, sched = resolve_intended_dose(
        db=db,
        patient_id=patient_id,
        medicine_name=req.medicine_name,
        medication_schedule_id=req.medication_schedule_id,
        scheduled_time=req.scheduled_time
    )

    if existing_log:
        if existing_log.status == "TAKEN":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dose of {existing_log.medicine_name} scheduled for {existing_log.scheduled_time.isoformat()} is already recorded as TAKEN and cannot be overwritten to MISSED."
            )
        existing_log.status = "MISSED"
        existing_log.stated_reason = req.stated_reason
        existing_log.actual_time = datetime.utcnow()
        existing_log.recorded_via = "PATIENT_PORTAL"
        log_entry = existing_log
    else:
        log_entry = MedicationLog(
            patient_id=patient_id,
            medication_schedule_id=req.medication_schedule_id or (sched.id if sched else None),
            medicine_name=req.medicine_name,
            dosage=req.dosage or (sched.dosage if sched else "Prescribed dose"),
            scheduled_time=target_sched_time,
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
        details={"medicine_name": req.medicine_name, "reason": req.stated_reason, "scheduled_time": target_sched_time.isoformat()},
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
            "sent_at": l.sent_at.isoformat(),
            "viewed_at": l.viewed_at.isoformat() if l.viewed_at else None,
            "is_read": l.viewed_at is not None
        }
        for l in logs
    ]

@router.get("/notifications/unread-count")
def get_unread_notification_count(
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
    count = db.execute(
        select(func.count(CommunicationLog.id)).where(
            CommunicationLog.patient_id == patient_id,
            CommunicationLog.viewed_at.is_(None)
        )
    ).scalar() or 0
    return {"unread_count": count}

@router.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
    log = db.get(CommunicationLog, notification_id)
    if not log or log.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Notification not found.")

    if log.viewed_at is None:
        log.viewed_at = datetime.utcnow()
        log.status = "VIEWED"
        db.commit()
        db.refresh(log)

    return {
        "id": log.id,
        "channel": log.channel,
        "message_type": log.message_type,
        "content": log.content,
        "status": log.status,
        "is_simulated": log.is_simulated,
        "sent_at": log.sent_at.isoformat(),
        "viewed_at": log.viewed_at.isoformat() if log.viewed_at else None,
        "is_read": True
    }

@router.put("/notifications/mark-all-read")
def mark_all_notifications_read(
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    patient_id = get_verified_patient_id(current_user, db)
    now = datetime.utcnow()
    unread_logs = db.execute(
        select(CommunicationLog).where(
            CommunicationLog.patient_id == patient_id,
            CommunicationLog.viewed_at.is_(None)
        )
    ).scalars().all()

    for log in unread_logs:
        log.viewed_at = now
        log.status = "VIEWED"

    db.commit()
    return {"marked_read_count": len(unread_logs), "status": "SUCCESS"}

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


# ----------------- FCM Device Token & Preferences Endpoints -----------------

@router.post("/notifications/device-token")
def register_device_token(
    req: DeviceTokenRegisterRequest,
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Registers or updates an FCM web push device token for the authenticated patient.
    Strictly isolated: Enforces patient ownership and prevents cross-patient IDOR.
    """
    patient_id = get_verified_patient_id(current_user, db)
    raw_token = req.fcm_token.strip()
    if not raw_token:
        raise HTTPException(status_code=400, detail="FCM token cannot be empty.")

    now = datetime.utcnow()

    # If token exists for another patient, deactivate it (device transfer / sharing)
    other_registrations = db.execute(
        select(PushDeviceRegistration).where(
            PushDeviceRegistration.fcm_token == raw_token,
            PushDeviceRegistration.patient_id != patient_id,
            PushDeviceRegistration.is_active == True
        )
    ).scalars().all()
    for other in other_registrations:
        other.is_active = False
        other.invalidated_at = now
        other.invalidation_reason = "DEVICE_REASSIGNED"

    # Check if registration exists for this patient
    existing = db.execute(
        select(PushDeviceRegistration).where(
            PushDeviceRegistration.patient_id == patient_id,
            PushDeviceRegistration.fcm_token == raw_token
        )
    ).scalars().first()

    if existing:
        existing.is_active = True
        existing.invalidated_at = None
        existing.invalidation_reason = None
        existing.device_type = req.device_type or existing.device_type
        if req.user_agent:
            existing.user_agent = req.user_agent
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        reg_id = existing.id
    else:
        new_reg = PushDeviceRegistration(
            patient_id=patient_id,
            fcm_token=raw_token,
            device_type=req.device_type or "web",
            user_agent=req.user_agent,
            is_active=True,
            push_enabled=True,
            created_at=now,
            updated_at=now
        )
        db.add(new_reg)
        db.commit()
        db.refresh(new_reg)
        reg_id = new_reg.id

    log_audit_event(
        db=db,
        event_type="FCM_TOKEN_REGISTERED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="push_device_registration",
        details={"registration_id": reg_id, "token_preview": mask_token(raw_token)},
        patient_id=patient_id
    )

    return {
        "status": "SUCCESS",
        "registration_id": reg_id,
        "is_active": True,
        "message": "FCM device token registered successfully."
    }


@router.delete("/notifications/device-token")
def unregister_device_token(
    req: Optional[DeviceTokenUnregisterRequest] = None,
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Deactivates FCM device token registration for the authenticated patient.
    Can deactivate a specific token or all active tokens (e.g. during logout).
    """
    patient_id = get_verified_patient_id(current_user, db)
    now = datetime.utcnow()

    target_token = req.fcm_token.strip() if req and req.fcm_token else None

    query = select(PushDeviceRegistration).where(
        PushDeviceRegistration.patient_id == patient_id,
        PushDeviceRegistration.is_active == True
    )
    if target_token:
        query = query.where(PushDeviceRegistration.fcm_token == target_token)

    active_regs = db.execute(query).scalars().all()
    count = len(active_regs)

    for reg in active_regs:
        reg.is_active = False
        reg.invalidated_at = now
        reg.invalidation_reason = "USER_DEREGISTERED"

    db.commit()

    log_audit_event(
        db=db,
        event_type="FCM_TOKEN_DEREGISTERED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="push_device_registration",
        details={"deactivated_count": count},
        patient_id=patient_id
    )

    return {
        "status": "SUCCESS",
        "deactivated_count": count,
        "message": f"Successfully deactivated {count} device registration(s)."
    }


@router.get("/notifications/preferences", response_model=NotificationPreferencesResponse)
def get_notification_preferences(
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Retrieves the authenticated patient's current push notification registration status and preferences.
    """
    patient_id = get_verified_patient_id(current_user, db)

    regs = db.execute(
        select(PushDeviceRegistration).where(
            PushDeviceRegistration.patient_id == patient_id
        ).order_by(desc(PushDeviceRegistration.created_at))
    ).scalars().all()

    active_regs = [r for r in regs if r.is_active]
    push_enabled = any(r.push_enabled for r in active_regs) if active_regs else True

    registered_at_str = regs[0].created_at.isoformat() if regs else None
    last_sent = [r.last_sent_at for r in regs if r.last_sent_at]
    last_sent_str = max(last_sent).isoformat() if last_sent else None

    return NotificationPreferencesResponse(
        push_enabled=push_enabled,
        has_registered_device=len(active_regs) > 0,
        active_devices_count=len(active_regs),
        registered_at=registered_at_str,
        last_sent_at=last_sent_str
    )


@router.put("/notifications/preferences")
def update_notification_preferences(
    req: NotificationPreferencesUpdateRequest,
    current_user: AuthUser = Depends(require_roles([UserRole.PATIENT, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Updates the authenticated patient's push notification enable/disable preference.
    """
    patient_id = get_verified_patient_id(current_user, db)

    regs = db.execute(
        select(PushDeviceRegistration).where(
            PushDeviceRegistration.patient_id == patient_id
        )
    ).scalars().all()

    for r in regs:
        r.push_enabled = req.push_enabled

    db.commit()

    log_audit_event(
        db=db,
        event_type="PUSH_PREFERENCES_UPDATED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="push_device_registration",
        details={"push_enabled": req.push_enabled},
        patient_id=patient_id
    )

    return {
        "status": "SUCCESS",
        "push_enabled": req.push_enabled,
        "message": f"Push notification preference updated to {'enabled' if req.push_enabled else 'disabled'}."
    }

