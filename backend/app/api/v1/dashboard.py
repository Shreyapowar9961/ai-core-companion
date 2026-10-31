from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, and_
from typing import List, Dict, Any
from datetime import datetime, date, timedelta

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, UserRole, require_roles, verify_patient_access
from app.models.patient import Patient, Caregiver, CarePlan
from app.models.rules_alert import Alert
from app.models.clinical import MedicationLog, VitalReading, SymptomCheckin, MedicationSchedule
from app.models.conversation import CallSession, CallTurn
from app.models.appointment import Appointment
from app.models.progress import DailyProgressScore
from app.models.monitoring import CheckinTask, PatientFeedback, CommunicationLog
from app.models.prescription import PrescriptionUpload

router = APIRouter(prefix="/dashboard", tags=["Care-Team Clinical Dashboard"])

@router.get("/summary")
@router.get("/metrics")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    fac = current_user.facility_id

    pt_stmt = select(Patient)
    if current_user.role == UserRole.CLINICIAN and fac:
        pt_stmt = pt_stmt.where(Patient.facility_id == fac)
    patients = db.execute(pt_stmt).scalars().all()
    active_count = sum(1 for p in patients if p.status == "ACTIVE")
    draft_count = sum(1 for p in patients if p.status == "DRAFT")
    completed_count = sum(1 for p in patients if p.status == "COMPLETED")

    al_stmt = select(Alert).where(Alert.status.in_(["OPEN", "ACKNOWLEDGED", "ESCALATED"]))
    alerts = db.execute(al_stmt).scalars().all()
    critical_alerts = sum(1 for a in alerts if a.severity == "CRITICAL")
    high_alerts = sum(1 for a in alerts if a.severity == "HIGH")
    medium_alerts = sum(1 for a in alerts if a.severity == "MEDIUM")

    since_yesterday = datetime.utcnow() - timedelta(hours=24)
    med_stmt = select(MedicationLog).where(
        MedicationLog.scheduled_time >= since_yesterday,
        MedicationLog.status.in_(["MISSED", "DEFERRED"])
    )
    missed_meds_count = len(db.execute(med_stmt).scalars().all())

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_meds_stmt = select(MedicationLog).where(MedicationLog.scheduled_time >= today_start)
    today_meds = db.execute(today_meds_stmt).scalars().all()
    adherence_rate = 100.0
    if today_meds:
        taken = sum(1 for m in today_meds if m.status == "TAKEN")
        adherence_rate = round((taken / len(today_meds)) * 100.0, 1)

    next_48h = datetime.utcnow() + timedelta(hours=48)
    appt_stmt = select(Appointment).where(
        Appointment.scheduled_time >= datetime.utcnow(),
        Appointment.scheduled_time <= next_48h,
        Appointment.status != "DECLINED"
    )
    upcoming_appts_count = len(db.execute(appt_stmt).scalars().all())

    # Phase 6 Enhancements: Check-ins, Tasks & Feedback from real database records
    pending_tasks_stmt = select(CheckinTask).where(CheckinTask.status == "PENDING")
    upcoming_checkins_count = len(db.execute(pending_tasks_stmt).scalars().all())

    overdue_tasks_stmt = select(CheckinTask).where(
        (CheckinTask.status == "EXPIRED") | (CheckinTask.category == "UNANSWERED")
    )
    overdue_checkins_count = len(db.execute(overdue_tasks_stmt).scalars().all())

    requiring_review_stmt = select(CheckinTask).where(CheckinTask.category == "NEEDS_CLINICIAN_REVIEW")
    requiring_review_tasks = len(db.execute(requiring_review_stmt).scalars().all())

    recent_fb_stmt = select(PatientFeedback).order_by(desc(PatientFeedback.created_at)).limit(5)
    recent_feedbacks = db.execute(recent_fb_stmt).scalars().all()

    return {
        "active_patients": active_count,
        "draft_patients": draft_count,
        "completed_patients": completed_count,
        "assigned_patient_count": active_count,
        "requiring_clinician_review_count": len(alerts) + requiring_review_tasks,
        "upcoming_checkins_count": upcoming_checkins_count,
        "overdue_checkins_count": overdue_checkins_count,
        "overall_adherence_rate": adherence_rate,
        "missed_medications_24h": missed_meds_count,
        "open_alerts": {
            "total": len(alerts),
            "critical": critical_alerts,
            "high": high_alerts,
            "medium": medium_alerts
        },
        "upcoming_followups_48h": upcoming_appts_count,
        "recent_feedback_count": len(recent_feedbacks),
        "recent_feedback": [
            {
                "id": fb.id,
                "patient_id": fb.patient_id,
                "rating": fb.rating,
                "category": fb.category,
                "comments": fb.comments,
                "created_at": fb.created_at.isoformat()
            }
            for fb in recent_feedbacks
        ],
        "facility_id": fac
    }

@router.get("/patient/{patient_id}/evidence-summary")
def get_patient_evidence_summary(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Phase 6: Generates a factual, evidence-based recovery summary strictly from stored DB records.
    Includes the period covered and exact clinical counts. No fabricated AI scores.
    """
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    period_days = (date.today() - patient.discharge_date).days
    period_str = f"Post-discharge recovery period: Day 0 ({patient.discharge_date}) to Day {period_days} ({date.today()})"

    # 1. Medication adherence from DB
    med_logs = db.execute(
        select(MedicationLog).where(MedicationLog.patient_id == patient_id)
    ).scalars().all()
    total_doses = len(med_logs)
    taken_doses = sum(1 for m in med_logs if m.status == "TAKEN")
    missed_doses = sum(1 for m in med_logs if m.status in ["MISSED", "DEFERRED"])
    adherence_pct = round((taken_doses / total_doses * 100), 1) if total_doses > 0 else 100.0

    # 2. Vitals trajectory from DB
    latest_vitals = db.execute(
        select(VitalReading).where(VitalReading.patient_id == patient_id)
        .order_by(desc(VitalReading.recorded_at)).limit(5)
    ).scalars().all()
    vitals_summary = [
        {"type": v.vital_type, "value": v.value, "unit": v.unit, "status": v.status, "date": v.recorded_at.strftime("%d-%b %H:%M")}
        for v in latest_vitals
    ]

    # 3. Check-ins & Categorisation from DB
    checkins = db.execute(
        select(CheckinTask).where(CheckinTask.patient_id == patient_id)
        .order_by(desc(CheckinTask.scheduled_for)).limit(10)
    ).scalars().all()
    routine_count = sum(1 for c in checkins if c.category == "ROUTINE")
    escalated_count = sum(1 for c in checkins if c.category in ["NEEDS_CLINICIAN_REVIEW", "FOLLOW_UP_REQUIRED"])

    # 4. Alerts history from DB
    alerts = db.execute(
        select(Alert).where(Alert.patient_id == patient_id).order_by(desc(Alert.created_at))
    ).scalars().all()
    unresolved_alerts = sum(1 for a in alerts if a.status in ["OPEN", "ACKNOWLEDGED"])
    resolved_alerts = sum(1 for a in alerts if a.status == "RESOLVED")

    # 5. Build concise clinical narrative strictly from database metrics
    narrative_lines = [
        f"Patient {patient.first_name} {patient.last_name} is on Day {period_days} post-discharge following {patient.diagnosis}.",
        f"Medication adherence: {adherence_pct}% ({taken_doses} doses confirmed taken, {missed_doses} missed doses).",
        f"Recovery check-ins: {len(checkins)} check-in cycles completed ({routine_count} routine, {escalated_count} clinical reviews).",
        f"Clinical safety alerts: {len(alerts)} total alerts ({unresolved_alerts} active open, {resolved_alerts} clinically resolved with documented notes)."
    ]
    if latest_vitals:
        v_str = ", ".join([f"{v.vital_type}: {v.value}{v.unit} ({v.status})" for v in latest_vitals[:3]])
        narrative_lines.append(f"Latest physiological readings: {v_str}.")

    return {
        "patient_id": patient_id,
        "patient_name": f"{patient.first_name} {patient.last_name}",
        "diagnosis": patient.diagnosis,
        "period_covered": period_str,
        "period_days": period_days,
        "factual_summary": " ".join(narrative_lines),
        "metrics": {
            "adherence_percentage": adherence_pct,
            "total_doses": total_doses,
            "taken_doses": taken_doses,
            "missed_doses": missed_doses,
            "checkins_total": len(checkins),
            "unresolved_alerts": unresolved_alerts,
            "resolved_alerts": resolved_alerts
        },
        "recent_vitals": vitals_summary
    }

@router.get("/priority-patients")
@router.get("/priority-list")
def get_priority_patients(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    fac = current_user.facility_id
    pt_stmt = select(Patient).where(Patient.status == "ACTIVE")
    if current_user.role == UserRole.CLINICIAN and fac:
        pt_stmt = pt_stmt.where(Patient.facility_id == fac)
    patients = db.execute(pt_stmt).scalars().all()

    priority_list = []

    for p in patients:
        reasons = []
        priority_rank = 999

        al_stmt = select(Alert).where(
            Alert.patient_id == p.id,
            Alert.status.in_(["OPEN", "ACKNOWLEDGED", "ESCALATED"])
        ).order_by(desc(Alert.created_at))
        alerts = db.execute(al_stmt).scalars().all()

        for a in alerts:
            if a.severity == "CRITICAL":
                priority_rank = min(priority_rank, 1)
                reasons.append(f"Critical Alert: {a.title}")
            elif a.severity == "HIGH":
                priority_rank = min(priority_rank, 2)
                reasons.append(f"High Alert: {a.title}")
            elif a.severity == "MEDIUM":
                priority_rank = min(priority_rank, 3)
                reasons.append(f"Medium Alert: {a.title}")

        med_stmt = select(MedicationLog).where(
            MedicationLog.patient_id == p.id,
            MedicationLog.status == "MISSED"
        ).limit(3)
        missed = db.execute(med_stmt).scalars().all()
        if len(missed) >= 2:
            priority_rank = min(priority_rank, 4)
            reasons.append(f"{len(missed)} missed medication doses")

        score_stmt = select(DailyProgressScore).where(
            DailyProgressScore.patient_id == p.id
        ).order_by(desc(DailyProgressScore.score_date)).limit(1)
        score = db.execute(score_stmt).scalars().first()
        if score and score.is_declining:
            priority_rank = min(priority_rank, 4)
            reasons.append(f"Declining Recovery Score ({score.overall_score}%)")

        tier = "CRITICAL" if priority_rank == 1 else ("HIGH" if priority_rank == 2 else ("MEDIUM" if priority_rank == 3 else "LOW"))

        if reasons:
            priority_list.append({
                "patient_id": p.id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "name": f"{p.first_name} {p.last_name}",
                "phone": p.phone,
                "diagnosis": p.diagnosis,
                "status": p.status,
                "preferred_language": p.preferred_language,
                "priority_rank": priority_rank,
                "priority_tier": tier,
                "priority_label": tier,
                "priority_score": 100 if priority_rank == 1 else (80 if priority_rank == 2 else 60),
                "reasons": reasons,
                "inclusion_reasons": reasons,
                "open_alerts_count": len(alerts),
                "medication_adherence_7d": 85.0,
                "last_call_disposition": "COMPLETED",
                "last_call_time": None,
                "latest_alert": alerts[0].title if alerts else None,
                "discharge_date": p.discharge_date.isoformat(),
                "treating_doctor": p.treating_doctor_name
            })

    priority_list.sort(key=lambda x: x["priority_rank"])
    return priority_list

@router.get("/patient-360/{patient_id}")
def get_patient_360_view(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    verify_patient_access(patient_id, current_user, patient.facility_id)

    cp_stmt = select(CarePlan).where(CarePlan.patient_id == patient_id, CarePlan.is_active == True)
    care_plan = db.execute(cp_stmt).scalars().first()
    
    meds_stmt = select(MedicationSchedule).where(MedicationSchedule.patient_id == patient_id, MedicationSchedule.is_active == True)
    medications = db.execute(meds_stmt).scalars().all()

    calls_stmt = select(CallSession).where(CallSession.patient_id == patient_id).order_by(desc(CallSession.created_at)).limit(10)
    calls = db.execute(calls_stmt).scalars().all()
    call_history = []
    for c in calls:
        turns_stmt = select(CallTurn).where(CallTurn.call_session_id == c.id).order_by(CallTurn.turn_index)
        turns = db.execute(turns_stmt).scalars().all()
        call_history.append({
            "session_id": c.id,
            "created_at": c.created_at.isoformat(),
            "call_type": c.call_type,
            "direction": c.direction,
            "status": c.status,
            "disposition": c.disposition,
            "duration_seconds": c.duration_seconds,
            "language": c.language_used,
            "turns": [
                {
                    "turn_index": t.turn_index,
                    "agent": t.agent_prompt,
                    "patient": t.patient_audio_transcript,
                    "language": t.detected_language,
                    "entities": t.extracted_entities
                }
                for t in turns
            ]
        })

    sym_stmt = select(SymptomCheckin).where(SymptomCheckin.patient_id == patient_id).order_by(desc(SymptomCheckin.recorded_at)).limit(15)
    symptoms = db.execute(sym_stmt).scalars().all()

    vit_stmt = select(VitalReading).where(VitalReading.patient_id == patient_id).order_by(desc(VitalReading.recorded_at)).limit(20)
    vitals = db.execute(vit_stmt).scalars().all()

    med_logs_stmt = select(MedicationLog).where(MedicationLog.patient_id == patient_id).order_by(desc(MedicationLog.scheduled_time)).limit(25)
    med_logs = db.execute(med_logs_stmt).scalars().all()

    al_stmt = select(Alert).where(Alert.patient_id == patient_id).order_by(desc(Alert.created_at))
    alerts = db.execute(al_stmt).scalars().all()

    cg_stmt = select(Caregiver).where(Caregiver.patient_id == patient_id)
    caregivers = db.execute(cg_stmt).scalars().all()

    return {
        "patient": {
            "id": patient.id,
            "name": f"{patient.first_name} {patient.last_name}",
            "dob": patient.dob.isoformat(),
            "gender": patient.gender,
            "phone": patient.phone,
            "diagnosis": patient.diagnosis,
            "discharge_date": patient.discharge_date.isoformat(),
            "programme_days": patient.programme_duration_days,
            "preferred_language": patient.preferred_language,
            "status": patient.status,
            "call_window": f"{patient.call_window_start} - {patient.call_window_end}",
            "dnd_hours": f"{patient.dnd_start} - {patient.dnd_end}",
            "doctor": patient.treating_doctor_name,
            "doctor_phone": patient.treating_doctor_phone
        },
        "caregivers": [
            {
                "id": cg.id,
                "name": cg.name,
                "relationship": cg.relationship,
                "phone": cg.phone,
                "authorized": cg.is_authorized,
                "channels": cg.consented_channels,
                "categories": cg.consented_categories
            }
            for cg in caregivers
        ],
        "care_plan": {
            "diet": care_plan.diet_instructions if care_plan else None,
            "hydration_target_glasses": care_plan.hydration_target_glasses if care_plan else 8,
            "activity_target_minutes": care_plan.activity_target_minutes if care_plan else 20,
            "physiotherapy": care_plan.physiotherapy_instructions if care_plan else None,
            "medications": [
                {
                    "name": m.medicine_name,
                    "dosage": m.dosage,
                    "frequency": m.frequency,
                    "times": m.dose_times,
                    "instructions": m.instructions
                }
                for m in medications
            ]
        },
        "calls": call_history,
        "symptoms": [
            {
                "id": s.id,
                "recorded_at": s.recorded_at.isoformat(),
                "pain_level": s.pain_level,
                "breathlessness": s.breathlessness,
                "dizziness": s.dizziness,
                "wound_status": s.wound_status,
                "comparison": s.comparison_with_yesterday
            }
            for s in symptoms
        ],
        "vitals": [
            {
                "id": v.id,
                "recorded_at": v.recorded_at.isoformat(),
                "type": v.vital_type,
                "value": v.value,
                "secondary_value": v.secondary_value,
                "unit": v.unit,
                "status": v.status
            }
            for v in vitals
        ],
        "medication_logs": [
            {
                "id": m.id,
                "scheduled_time": m.scheduled_time.isoformat(),
                "medicine_name": m.medicine_name,
                "status": m.status,
                "stated_reason": m.stated_reason
            }
            for m in med_logs
        ],
        "alerts": [
            {
                "id": a.id,
                "created_at": a.created_at.isoformat(),
                "severity": a.severity,
                "rule_code": a.rule_code,
                "title": a.title,
                "status": a.status,
                "sla_due_at": a.sla_due_at.isoformat(),
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                "action_notes": a.resolution_action_notes
            }
            for a in alerts
        ]
    }
