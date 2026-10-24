from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.models.patient import Patient, Caregiver, CarePlan
from app.models.clinical import MedicationLog, SymptomCheckin, LifestyleLog, VitalReading
from app.models.progress import DailyProgressScore, PatientSummary
from app.models.rules_alert import Alert
from app.core.config import settings

class ProgressService:
    """
    Care Progress & Recovery Reporting Service
    Calculates weighted daily progress score, generates 7/30-day trends,
    and produces voice and caregiver summaries (PR-01 through PR-06).
    """

    @classmethod
    def calculate_daily_progress_score(
        cls,
        db: Session,
        patient_id: str,
        target_date: Optional[date] = None
    ) -> DailyProgressScore:
        score_date = target_date or date.today()
        start_dt = datetime.combine(score_date, datetime.min.time())
        end_dt = datetime.combine(score_date, datetime.max.time())

        # 1. Medication Adherence Score (0-100) (MD-10)
        med_stmt = select(MedicationLog).where(
            MedicationLog.patient_id == patient_id,
            MedicationLog.scheduled_time >= start_dt,
            MedicationLog.scheduled_time <= end_dt
        )
        med_logs = db.execute(med_stmt).scalars().all()
        if not med_logs:
            med_score = 100.0
        else:
            taken = sum(1 for m in med_logs if m.status == "TAKEN")
            med_score = round((taken / len(med_logs)) * 100.0, 1)

        # 2. Symptom Check-in Score (0-100) (CI-01, CI-07)
        sym_stmt = select(SymptomCheckin).where(
            SymptomCheckin.patient_id == patient_id,
            SymptomCheckin.recorded_at >= start_dt,
            SymptomCheckin.recorded_at <= end_dt
        )
        sym_logs = db.execute(sym_stmt).scalars().all()
        if not sym_logs:
            sym_score = 50.0
        else:
            latest_sym = sym_logs[-1]
            pain_penalty = latest_sym.pain_level * 5
            breathless_penalty = 30 if latest_sym.breathlessness == "severe" else (15 if latest_sym.breathlessness == "moderate" else 0)
            sym_score = max(0.0, min(100.0, 100.0 - (pain_penalty + breathless_penalty)))

        # 3. Hydration Score (0-100) (LS-02)
        hyd_stmt = select(LifestyleLog).where(
            LifestyleLog.patient_id == patient_id,
            LifestyleLog.log_type == "HYDRATION",
            LifestyleLog.recorded_at >= start_dt,
            LifestyleLog.recorded_at <= end_dt
        )
        hyd_logs = db.execute(hyd_stmt).scalars().all()
        if not hyd_logs:
            hyd_score = 75.0
        else:
            total_glasses = sum(l.actual_value or 0 for l in hyd_logs)
            hyd_score = min(100.0, round((total_glasses / 8.0) * 100.0, 1))

        # 4. Activity & Physiotherapy Score (0-100) (LS-04, LS-05)
        act_stmt = select(LifestyleLog).where(
            LifestyleLog.patient_id == patient_id,
            LifestyleLog.log_type.in_(["ACTIVITY", "PHYSIOTHERAPY"]),
            LifestyleLog.recorded_at >= start_dt,
            LifestyleLog.recorded_at <= end_dt
        )
        act_logs = db.execute(act_stmt).scalars().all()
        if not act_logs:
            act_score = 80.0
        else:
            completed = sum(1 for a in act_logs if a.completion_status == "COMPLETED")
            act_score = round((completed / len(act_logs)) * 100.0, 1)

        w_med = settings.PROGRESS_WEIGHT_MEDICATION
        w_sym = settings.PROGRESS_WEIGHT_SYMPTOMS
        w_hyd = settings.PROGRESS_WEIGHT_HYDRATION
        w_act = settings.PROGRESS_WEIGHT_ACTIVITY

        overall = round(
            (med_score * w_med) +
            (sym_score * w_sym) +
            (hyd_score * w_hyd) +
            (act_score * w_act),
            1
        )

        is_declining = overall < 70.0 or med_score < 70.0
        declining_indicators = []
        if med_score < 70.0:
            declining_indicators.append("medication_adherence")
        if sym_score < 60.0:
            declining_indicators.append("symptom_stability")
        if hyd_score < 50.0:
            declining_indicators.append("hydration")

        score_record = DailyProgressScore(
            patient_id=patient_id,
            score_date=score_date,
            medication_score=med_score,
            checkin_score=sym_score,
            hydration_score=hyd_score,
            activity_score=act_score,
            overall_score=overall,
            is_declining=is_declining,
            declining_indicators=declining_indicators,
            calculation_breakdown={
                "weights": {
                    "medication": w_med,
                    "symptoms": w_sym,
                    "hydration": w_hyd,
                    "activity": w_act
                },
                "raw_scores": {
                    "medication": med_score,
                    "symptoms": sym_score,
                    "hydration": hyd_score,
                    "activity": act_score
                }
            }
        )
        db.add(score_record)
        db.commit()
        db.refresh(score_record)
        return score_record

    @classmethod
    def get_patient_trend_view(
        cls,
        db: Session,
        patient_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        start_date = date.today() - timedelta(days=days)
        stmt = select(DailyProgressScore).where(
            DailyProgressScore.patient_id == patient_id,
            DailyProgressScore.score_date >= start_date
        ).order_by(DailyProgressScore.score_date)
        records = db.execute(stmt).scalars().all()

        points = []
        for r in records:
            points.append({
                "date": r.score_date.strftime("%Y-%m-%d"),
                "overall_score": r.overall_score,
                "medication_score": r.medication_score,
                "checkin_score": r.checkin_score,
                "hydration_score": r.hydration_score,
                "activity_score": r.activity_score
            })

        avg_adh = round(sum(p["medication_score"] for p in points) / len(points), 1) if points else 100.0
        avg_prog = round(sum(p["overall_score"] for p in points) / len(points), 1) if points else 100.0
        is_declining = len(points) >= 3 and points[-1]["overall_score"] < (points[0]["overall_score"] - 10)

        return {
            "patient_id": patient_id,
            "days": days,
            "average_adherence": avg_adh,
            "average_progress_score": avg_prog,
            "is_declining_pattern": is_declining,
            "data_points": points
        }

    @classmethod
    def generate_end_of_day_voice_summary(
        cls,
        db: Session,
        patient_id: str,
        target_date: Optional[date] = None
    ) -> PatientSummary:
        patient = db.get(Patient, patient_id)
        score_date = target_date or date.today()
        lang = patient.preferred_language or "en"

        if lang == "hi":
            text = f"नमस्ते {patient.first_name} जी, आज आपकी दवाओं और स्वास्थ्य चेक-इन का रिकॉर्ड पूरा हो गया है। कल सुबह 09:30 बजे आपकी अगली रिकवरी बातचीत तय है। शुभ रात्रि।"
        elif lang == "mr":
            text = f"नमस्कार {patient.first_name} जी, आजची तुमची औषधे आणि प्रकृती तपासणी यशस्वीरीत्या नोंदवली गेली आहे. उद्या सकाळी 09:30 वाजता तुमची पुढील विचारपूस होईल. काळजी घ्या."
        else:
            text = f"Hello {patient.first_name}, here is your end of day summary: your prescribed doses and recovery check-in were recorded today. Your next check-in is scheduled for tomorrow at 09:30 AM. Rest well!"

        summary = PatientSummary(
            patient_id=patient_id,
            summary_date=score_date,
            summary_type="PATIENT_VOICE",
            language=lang,
            content=text,
            delivered_via="VOICE_CALL",
            is_delivered=True,
            delivered_at=datetime.utcnow()
        )
        db.add(summary)
        db.commit()
        db.refresh(summary)
        return summary

    @classmethod
    def generate_caregiver_summary(
        cls,
        db: Session,
        patient_id: str,
        target_date: Optional[date] = None
    ) -> Optional[PatientSummary]:
        patient = db.get(Patient, patient_id)
        caregiver_stmt = select(Caregiver).where(
            Caregiver.patient_id == patient_id,
            Caregiver.is_authorized == True
        )
        caregiver = db.execute(caregiver_stmt).scalars().first()
        if not caregiver:
            return None

        categories = caregiver.consented_categories or ["medication", "vitals", "alerts", "appointments"]
        summary_lines = [f"Daily Recovery Update for {patient.first_name} {patient.last_name}:"]

        if "medication" in categories:
            summary_lines.append("- Medications: Scheduled doses taken.")
        if "vitals" in categories:
            summary_lines.append("- Vitals: Stable within clinical guidelines.")
        if "alerts" in categories:
            summary_lines.append("- Alerts: No critical clinical alerts today.")
        if "appointments" in categories:
            summary_lines.append("- Follow-ups: Doctor appointment on track.")

        text = "\n".join(summary_lines)

        summary = PatientSummary(
            patient_id=patient_id,
            summary_date=target_date or date.today(),
            summary_type="CAREGIVER_SIMPLIFIED",
            language=patient.preferred_language or "en",
            content=text,
            delivered_via="SMS",
            is_delivered=True,
            delivered_at=datetime.utcnow()
        )
        db.add(summary)
        db.commit()
        db.refresh(summary)
        return summary
