import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.models.rules_alert import EscalationRule, Alert, AlertActionLog
from app.models.clinical import VitalReading, SymptomCheckin, MedicationLog, VitalsThreshold
from app.models.conversation import CallSession
from app.models.patient import Patient, Caregiver, Consent
from app.models.progress import DailyProgressScore
from app.core.config import settings

class RulesEngine:
    """
    DETERMINISTIC CLINICAL RULES ENGINE
    -----------------------------------
    Architecture Mandate: All clinical escalation logic and alerting MUST run in a
    deterministic, clinician-configured rules engine in the backend, NEVER in the LLM.
    Do not invent clinical thresholds.
    """

    @staticmethod
    def get_sla_due_time(severity: str) -> datetime:
        now = datetime.utcnow()
        if severity == "CRITICAL":
            return now + timedelta(minutes=settings.ALERT_SLA_CRITICAL_MINUTES)
        elif severity == "HIGH":
            return now + timedelta(minutes=settings.ALERT_SLA_HIGH_MINUTES)
        elif severity == "MEDIUM":
            return now + timedelta(minutes=settings.ALERT_SLA_MEDIUM_MINUTES)
        else: # INFO
            return now + timedelta(minutes=settings.ALERT_SLA_INFO_MINUTES)

    @classmethod
    def evaluate_vital_reading(
        cls,
        db: Session,
        patient_id: str,
        vital_type: str,
        value: Optional[float],
        secondary_value: Optional[float] = None,
        unit: str = ""
    ) -> Tuple[str, Optional[Alert]]:
        """
        Evaluates a vital reading against clinician-defined thresholds (VT-03, VT-04, ES-01)
        """
        if value is None:
            return "NOT_PROVIDED", None

        # Fetch clinician thresholds for this patient and vital_type
        stmt = select(VitalsThreshold).where(
            VitalsThreshold.patient_id == patient_id,
            VitalsThreshold.vital_type == vital_type
        )
        threshold = db.execute(stmt).scalars().first()
        
        # Plausibility check (VT-02)
        plausible_min = threshold.plausible_min if threshold else 0.0
        plausible_max = threshold.plausible_max if threshold else 9999.0
        
        if vital_type == "SPO2":
            plausible_min, plausible_max = 50.0, 100.0
        elif vital_type == "BP_SYSTOLIC":
            plausible_min, plausible_max = 50.0, 260.0
        elif vital_type == "BP_DIASTOLIC":
            plausible_min, plausible_max = 30.0, 160.0
        elif vital_type == "BLOOD_GLUCOSE":
            plausible_min, plausible_max = 30.0, 600.0
        elif vital_type == "TEMPERATURE":
            plausible_min, plausible_max = 90.0, 110.0
        elif vital_type == "PULSE":
            plausible_min, plausible_max = 30.0, 240.0

        if value < plausible_min or value > plausible_max:
            return "IMPLAUSIBLE", None

        critical_min = threshold.critical_min if threshold else None
        critical_max = threshold.critical_max if threshold else None
        warning_min = threshold.warning_min if threshold else None
        warning_max = threshold.warning_max if threshold else None

        if vital_type == "SPO2":
            critical_min = critical_min or 88.0
            warning_min = warning_min or 92.0
        elif vital_type == "BP_SYSTOLIC":
            critical_max = critical_max or 180.0
            warning_max = warning_max or 150.0
            critical_min = critical_min or 85.0
            warning_min = warning_min or 95.0
        elif vital_type == "BLOOD_GLUCOSE":
            critical_max = critical_max or 300.0
            critical_min = critical_min or 60.0
            warning_max = warning_max or 200.0
            warning_min = warning_min or 70.0
        elif vital_type == "TEMPERATURE":
            critical_max = critical_max or 103.0
            warning_max = warning_max or 100.4

        # Check Critical breach
        is_critical = False
        if critical_min is not None and value < critical_min:
            is_critical = True
        if critical_max is not None and value > critical_max:
            is_critical = True

        if is_critical:
            alert = Alert(
                patient_id=patient_id,
                rule_code=f"RULE_VITAL_{vital_type}_CRITICAL",
                severity="CRITICAL",
                title=f"Critical {vital_type} Breach: {value} {unit}",
                description=f"Patient reported {vital_type} of {value} {unit}, which breached critical safety boundaries ({critical_min} - {critical_max} {unit}).",
                supporting_data={
                    "vital_type": vital_type,
                    "value": value,
                    "secondary_value": secondary_value,
                    "unit": unit,
                    "critical_min": critical_min,
                    "critical_max": critical_max
                },
                status="OPEN",
                sla_due_at=cls.get_sla_due_time("CRITICAL")
            )
            db.add(alert)
            db.flush()
            
            action_log = AlertActionLog(
                alert_id=alert.id,
                user_id="RULES_ENGINE",
                user_name="Deterministic Clinical Rules Engine",
                action="CREATED",
                notes=f"Auto-triggered by vital threshold breach: {vital_type}={value}"
            )
            db.add(action_log)
            db.commit()
            return "CRITICAL", alert

        # Check Warning breach
        is_warning = False
        if warning_min is not None and value < warning_min:
            is_warning = True
        if warning_max is not None and value > warning_max:
            is_warning = True

        if is_warning:
            alert = Alert(
                patient_id=patient_id,
                rule_code=f"RULE_VITAL_{vital_type}_WARNING",
                severity="HIGH",
                title=f"Elevated {vital_type}: {value} {unit}",
                description=f"Patient reported {vital_type} of {value} {unit}, entering clinician-configured warning zone.",
                supporting_data={
                    "vital_type": vital_type,
                    "value": value,
                    "secondary_value": secondary_value,
                    "unit": unit,
                    "warning_min": warning_min,
                    "warning_max": warning_max
                },
                status="OPEN",
                sla_due_at=cls.get_sla_due_time("HIGH")
            )
            db.add(alert)
            db.flush()
            
            action_log = AlertActionLog(
                alert_id=alert.id,
                user_id="RULES_ENGINE",
                user_name="Deterministic Clinical Rules Engine",
                action="CREATED",
                notes=f"Auto-triggered by warning threshold: {vital_type}={value}"
            )
            db.add(action_log)
            db.commit()
            return "WARNING", alert

        return "NORMAL", None

    @classmethod
    def evaluate_symptom_checkin(
        cls,
        db: Session,
        patient_id: str,
        current_checkin: SymptomCheckin
    ) -> List[Alert]:
        """
        Evaluates symptom check-in for red flags (ES-03) and sustained worsening trends (CI-05).
        """
        generated_alerts: List[Alert] = []

        # 1. Red-Flag Presentation Checks (ES-03)
        red_flag_reasons = []
        if current_checkin.pain_level is not None and current_checkin.pain_level >= 8:
            red_flag_reasons.append(f"Severe acute pain reported (Score: {current_checkin.pain_level}/10)")
        if current_checkin.breathlessness in ["severe", "worsened_severe"]:
            red_flag_reasons.append("Severe breathlessness reported")
        if current_checkin.fever in ["severe", "high"]:
            red_flag_reasons.append("High fever reported")
        if current_checkin.wound_status == "discharge":
            red_flag_reasons.append("Purulent surgical wound discharge reported")

        if red_flag_reasons:
            alert = Alert(
                patient_id=patient_id,
                rule_code="RULE_RED_FLAG_EMERGENCY",
                severity="CRITICAL",
                title="RED-FLAG Clinical Emergency Presentation",
                description="; ".join(red_flag_reasons) + ". Immediate clinical evaluation and emergency script delivery required.",
                supporting_data={
                    "reasons": red_flag_reasons,
                    "pain_level": current_checkin.pain_level,
                    "breathlessness": current_checkin.breathlessness,
                    "fever": current_checkin.fever,
                    "wound_status": current_checkin.wound_status,
                    "checkin_id": current_checkin.id
                },
                status="OPEN",
                sla_due_at=cls.get_sla_due_time("CRITICAL")
            )
            db.add(alert)
            db.flush()
            db.add(AlertActionLog(
                alert_id=alert.id,
                user_id="RULES_ENGINE",
                user_name="Deterministic Clinical Rules Engine",
                action="CREATED",
                notes="Red-flag symptom emergency triggered"
            ))
            generated_alerts.append(alert)

        # 2. Sustained Worsening Trend Detection (CI-05)
        prev_stmt = select(SymptomCheckin).where(
            SymptomCheckin.patient_id == patient_id,
            SymptomCheckin.id != current_checkin.id
        ).order_by(desc(SymptomCheckin.recorded_at)).limit(3)
        previous_checkins = db.execute(prev_stmt).scalars().all()

        if previous_checkins:
            worsened_breathlessness_days = 0
            if current_checkin.comparison_with_yesterday and current_checkin.comparison_with_yesterday.get("breathlessness") == "worsened":
                worsened_breathlessness_days += 1
            for prev in previous_checkins[:2]:
                if (prev.comparison_with_yesterday and prev.comparison_with_yesterday.get("breathlessness") == "worsened") or prev.breathlessness in ["moderate", "severe"]:
                    worsened_breathlessness_days += 1

            if worsened_breathlessness_days >= 2:
                alert = Alert(
                    patient_id=patient_id,
                    rule_code="RULE_SYMPTOM_SUSTAINED_WORSENING_BREATHLESSNESS",
                    severity="HIGH",
                    title="Sustained Worsening Breathlessness Trend",
                    description=f"Patient has exhibited a deteriorating breathlessness trend across {worsened_breathlessness_days} consecutive check-ins.",
                    supporting_data={
                        "symptom": "breathlessness",
                        "consecutive_worsened_days": worsened_breathlessness_days,
                        "current_status": current_checkin.breathlessness
                    },
                    status="OPEN",
                    sla_due_at=cls.get_sla_due_time("HIGH")
                )
                db.add(alert)
                db.flush()
                db.add(AlertActionLog(
                    alert_id=alert.id,
                    user_id="RULES_ENGINE",
                    user_name="Deterministic Clinical Rules Engine",
                    action="CREATED",
                    notes="Sustained breathlessness deterioration detected across multiple days"
                ))
                generated_alerts.append(alert)

            if current_checkin.comparison_with_yesterday and current_checkin.comparison_with_yesterday.get("pain") == "worsened" and (current_checkin.pain_level is not None and current_checkin.pain_level >= 5):
                prev_pain = (previous_checkins[0].pain_level or 0) if previous_checkins else 0
                if current_checkin.pain_level > prev_pain:
                    alert = Alert(
                        patient_id=patient_id,
                        rule_code="RULE_SYMPTOM_WORSENING_PAIN",
                        severity="MEDIUM",
                        title=f"Worsening Pain Trend (Score: {current_checkin.pain_level}/10)",
                        description=f"Patient pain increased from {prev_pain}/10 to {current_checkin.pain_level}/10.",
                        supporting_data={
                            "symptom": "pain",
                            "previous_score": prev_pain,
                            "current_score": current_checkin.pain_level
                        },
                        status="OPEN",
                        sla_due_at=cls.get_sla_due_time("MEDIUM")
                    )
                    db.add(alert)
                    db.flush()
                    db.add(AlertActionLog(
                        alert_id=alert.id,
                        user_id="RULES_ENGINE",
                        user_name="Deterministic Clinical Rules Engine",
                        action="CREATED",
                        notes=f"Pain score increased: {prev_pain} -> {current_checkin.pain_level}"
                    ))
                    generated_alerts.append(alert)

        db.commit()
        return generated_alerts

    @classmethod
    def evaluate_medication_miss(
        cls,
        db: Session,
        patient_id: str,
        medicine_name: str
    ) -> Optional[Alert]:
        """
        Detect repeated medication misses against configurable threshold (MD-05).
        """
        stmt = select(MedicationLog).where(
            MedicationLog.patient_id == patient_id,
            MedicationLog.medicine_name == medicine_name
        ).order_by(desc(MedicationLog.scheduled_time)).limit(3)
        recent_logs = db.execute(stmt).scalars().all()

        missed_count = sum(1 for m in recent_logs if m.status in ["MISSED", "DEFERRED"])
        if missed_count >= 2:
            alert = Alert(
                patient_id=patient_id,
                rule_code="RULE_MED_REPEATED_MISS",
                severity="HIGH",
                title=f"Repeated Missed Doses: {medicine_name}",
                description=f"Patient has missed or deferred {missed_count} consecutive scheduled doses of {medicine_name}.",
                supporting_data={
                    "medicine_name": medicine_name,
                    "consecutive_misses": missed_count,
                    "recent_reasons": [m.stated_reason for m in recent_logs if m.stated_reason]
                },
                status="OPEN",
                sla_due_at=cls.get_sla_due_time("HIGH")
            )
            db.add(alert)
            db.flush()
            db.add(AlertActionLog(
                alert_id=alert.id,
                user_id="RULES_ENGINE",
                user_name="Deterministic Clinical Rules Engine",
                action="CREATED",
                notes=f"Triggered by repeated misses of {medicine_name}"
            ))
            db.commit()
            return alert
        return None

    @classmethod
    def evaluate_contact_failure(
        cls,
        db: Session,
        patient_id: str,
        retry_count: int,
        retry_limit: int,
        last_disposition: str
    ) -> Optional[Alert]:
        """
        CM-02: Escalate to caregiver and care team once configured contact attempts are exhausted.
        """
        if retry_count >= retry_limit:
            alert = Alert(
                patient_id=patient_id,
                rule_code="RULE_CONTACT_FAILURE_EXHAUSTED",
                severity="HIGH",
                title=f"Patient Unreachable: {retry_count} Attempts Exhausted",
                description=f"Outbound scheduled calls could not reach patient after {retry_count} attempts. Last disposition: {last_disposition}.",
                supporting_data={
                    "attempts": retry_count,
                    "limit": retry_limit,
                    "last_disposition": last_disposition
                },
                status="OPEN",
                sla_due_at=cls.get_sla_due_time("HIGH")
            )
            db.add(alert)
            db.flush()
            db.add(AlertActionLog(
                alert_id=alert.id,
                user_id="RULES_ENGINE",
                user_name="Deterministic Clinical Rules Engine",
                action="CREATED",
                notes=f"Contact attempts exhausted ({retry_count}/{retry_limit})"
            ))
            db.commit()
            return alert
        return None

    @classmethod
    def evaluate_composite_decline(
        cls,
        db: Session,
        patient_id: str
    ) -> Optional[Alert]:
        """
        ES-08: Flag a declining pattern across configured indicators for clinical review.
        """
        now = datetime.utcnow()
        three_days_ago = now - timedelta(days=3)

        med_stmt = select(MedicationLog).where(
            MedicationLog.patient_id == patient_id,
            MedicationLog.scheduled_time >= three_days_ago,
            MedicationLog.status == "MISSED"
        )
        missed_meds = len(db.execute(med_stmt).scalars().all())

        sym_stmt = select(SymptomCheckin).where(
            SymptomCheckin.patient_id == patient_id,
            SymptomCheckin.recorded_at >= three_days_ago
        ).order_by(desc(SymptomCheckin.recorded_at)).limit(3)
        checkins = db.execute(sym_stmt).scalars().all()

        worsened_symptoms_count = 0
        for c in checkins:
            for k, v in c.comparison_with_yesterday.items():
                if v == "worsened":
                    worsened_symptoms_count += 1

        score_stmt = select(DailyProgressScore).where(
            DailyProgressScore.patient_id == patient_id
        ).order_by(desc(DailyProgressScore.score_date)).limit(3)
        scores = db.execute(score_stmt).scalars().all()

        score_drop = False
        if len(scores) >= 2 and scores[0].overall_score < (scores[-1].overall_score - 15.0):
            score_drop = True

        indicators_flagged = []
        if missed_meds > 0:
            indicators_flagged.append(f"{missed_meds} missed medications in last 72 hours")
        if worsened_symptoms_count >= 2:
            indicators_flagged.append(f"{worsened_symptoms_count} symptoms reported as worsened")
        if score_drop:
            indicators_flagged.append(f"Care Progress score dropped by >15% over last 3 days")

        if len(indicators_flagged) >= 2:
            existing_stmt = select(Alert).where(
                Alert.patient_id == patient_id,
                Alert.rule_code == "RULE_COMPOSITE_DECLINE_REVIEW",
                Alert.status.in_(["OPEN", "ACKNOWLEDGED", "ESCALATED"])
            )
            existing = db.execute(existing_stmt).scalars().first()
            if not existing:
                alert = Alert(
                    patient_id=patient_id,
                    rule_code="RULE_COMPOSITE_DECLINE_REVIEW",
                    severity="HIGH",
                    title="Composite Health Pattern Decline Detected",
                    description="Patient exhibits a multi-factor declining pattern across indicators: " + "; ".join(indicators_flagged),
                    supporting_data={
                        "indicators": indicators_flagged,
                        "missed_meds": missed_meds,
                        "worsened_symptoms_count": worsened_symptoms_count,
                        "score_drop": score_drop
                    },
                    status="OPEN",
                    sla_due_at=cls.get_sla_due_time("HIGH")
                )
                db.add(alert)
                db.flush()
                db.add(AlertActionLog(
                    alert_id=alert.id,
                    user_id="RULES_ENGINE",
                    user_name="Deterministic Clinical Rules Engine",
                    action="CREATED",
                    notes="Composite decline detected across multiple clinical indicators"
                ))
                db.commit()
                return alert

        return None
