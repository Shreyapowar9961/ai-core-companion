from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from app.models.audit import AuditLog, ConfigAuditLog
from app.models.conversation import CallSession, CallTurn
from app.models.clinical import VitalReading, SymptomCheckin, MedicationLog, LifestyleLog
from app.models.rules_alert import Alert
from app.models.patient import Consent

def log_audit_event(
    db: Session,
    event_type: str,
    actor_id: str,
    actor_role: str,
    resource: str,
    details: Dict[str, Any],
    patient_id: Optional[str] = None
) -> AuditLog:
    """
    GV-03: Maintain an immutable audit trail of calls, reminders, responses,
    confirmations, alerts, escalations, handoffs, consent and access.
    """
    entry = AuditLog(
        event_type=event_type,
        actor_id=actor_id,
        actor_role=actor_role,
        patient_id=patient_id,
        resource=resource,
        details_json=details,
        created_at=datetime.utcnow()
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def log_config_audit(
    db: Session,
    config_type: str,
    item_id: str,
    changed_by: str,
    new_value: Dict[str, Any],
    old_value: Optional[Dict[str, Any]] = None,
    change_reason: Optional[str] = None
) -> ConfigAuditLog:
    """
    GV-04: Log all configuration changes to schedules, thresholds, questionnaires,
    rules and content, with previous and new values.
    """
    entry = ConfigAuditLog(
        config_type=config_type,
        item_id=item_id,
        changed_by=changed_by,
        old_value_json=old_value,
        new_value_json=new_value,
        change_reason=change_reason,
        created_at=datetime.utcnow()
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def reconstruct_patient_journey(
    db: Session,
    patient_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    GV-05: Enable reconstruction of a patient's complete interaction history
    for any period by an authorised user.
    """
    journey: List[Dict[str, Any]] = []

    # 1. Audit logs
    audit_stmt = select(AuditLog).where(AuditLog.patient_id == patient_id)
    if start_date:
        audit_stmt = audit_stmt.where(AuditLog.created_at >= start_date)
    if end_date:
        audit_stmt = audit_stmt.where(AuditLog.created_at <= end_date)
    audit_results = db.execute(audit_stmt).scalars().all()
    for a in audit_results:
        journey.append({
            "timestamp": a.created_at.isoformat(),
            "type": "AUDIT_EVENT",
            "subtype": a.event_type,
            "actor": f"{a.actor_role} ({a.actor_id})",
            "resource": a.resource,
            "details": a.details_json
        })

    # 2. Call sessions & transcripts
    call_stmt = select(CallSession).where(CallSession.patient_id == patient_id)
    if start_date:
        call_stmt = call_stmt.where(CallSession.created_at >= start_date)
    if end_date:
        call_stmt = call_stmt.where(CallSession.created_at <= end_date)
    calls = db.execute(call_stmt).scalars().all()
    for c in calls:
        turns_stmt = select(CallTurn).where(CallTurn.call_session_id == c.id).order_by(CallTurn.turn_index)
        turns = db.execute(turns_stmt).scalars().all()
        journey.append({
            "timestamp": c.created_at.isoformat(),
            "type": "CALL_INTERACTION",
            "subtype": c.call_type,
            "direction": c.direction,
            "status": c.status,
            "disposition": c.disposition,
            "language": c.language_used,
            "duration_seconds": c.duration_seconds,
            "turns_count": len(turns),
            "transcript_summary": [
                {
                    "turn": t.turn_index,
                    "agent": t.agent_prompt,
                    "patient": t.patient_audio_transcript,
                    "language": t.detected_language,
                    "unanswered": t.was_unanswered
                }
                for t in turns
            ]
        })

    # 3. Vitals recorded
    vitals_stmt = select(VitalReading).where(VitalReading.patient_id == patient_id)
    if start_date:
        vitals_stmt = vitals_stmt.where(VitalReading.recorded_at >= start_date)
    if end_date:
        vitals_stmt = vitals_stmt.where(VitalReading.recorded_at <= end_date)
    vitals = db.execute(vitals_stmt).scalars().all()
    for v in vitals:
        journey.append({
            "timestamp": v.recorded_at.isoformat(),
            "type": "VITAL_READING",
            "subtype": v.vital_type,
            "value": v.value,
            "secondary_value": v.secondary_value,
            "unit": v.unit,
            "status": v.status,
            "voice_confirmed": v.voice_confirmed
        })

    # 4. Symptom Checkins
    checkin_stmt = select(SymptomCheckin).where(SymptomCheckin.patient_id == patient_id)
    if start_date:
        checkin_stmt = checkin_stmt.where(SymptomCheckin.recorded_at >= start_date)
    if end_date:
        checkin_stmt = checkin_stmt.where(SymptomCheckin.recorded_at <= end_date)
    checkins = db.execute(checkin_stmt).scalars().all()
    for s in checkins:
        journey.append({
            "timestamp": s.recorded_at.isoformat(),
            "type": "SYMPTOM_CHECKIN",
            "subtype": s.checkin_type,
            "pain_level": s.pain_level,
            "breathlessness": s.breathlessness,
            "dizziness": s.dizziness,
            "weakness": s.weakness,
            "wound_status": s.wound_status,
            "comparison": s.comparison_with_yesterday,
            "other_verbatim": s.other_symptoms_verbatim
        })

    # 5. Medication logs
    med_stmt = select(MedicationLog).where(MedicationLog.patient_id == patient_id)
    if start_date:
        med_stmt = med_stmt.where(MedicationLog.scheduled_time >= start_date)
    if end_date:
        med_stmt = med_stmt.where(MedicationLog.scheduled_time <= end_date)
    meds = db.execute(med_stmt).scalars().all()
    for m in meds:
        journey.append({
            "timestamp": (m.actual_time or m.scheduled_time).isoformat(),
            "type": "MEDICATION_EVENT",
            "subtype": m.medicine_name,
            "dosage": m.dosage,
            "status": m.status,
            "stated_reason": m.stated_reason,
            "deferral_count": m.deferral_count
        })

    # 6. Clinical Alerts
    alert_stmt = select(Alert).where(Alert.patient_id == patient_id)
    if start_date:
        alert_stmt = alert_stmt.where(Alert.created_at >= start_date)
    if end_date:
        alert_stmt = alert_stmt.where(Alert.created_at <= end_date)
    alerts = db.execute(alert_stmt).scalars().all()
    for al in alerts:
        journey.append({
            "timestamp": al.created_at.isoformat(),
            "type": "CLINICAL_ALERT",
            "subtype": al.rule_code,
            "severity": al.severity,
            "title": al.title,
            "status": al.status,
            "sla_due_at": al.sla_due_at.isoformat(),
            "acknowledged_at": al.acknowledged_at.isoformat() if al.acknowledged_at else None,
            "resolved_at": al.resolved_at.isoformat() if al.resolved_at else None,
            "action_notes": al.resolution_action_notes
        })

    journey.sort(key=lambda x: x["timestamp"])
    return journey
