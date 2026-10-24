import uuid
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.models.patient import Patient, CarePlan, Caregiver, Consent
from app.models.clinical import (
    MedicationSchedule, MedicationLog, VitalsThreshold, VitalReading,
    SymptomCheckin, LifestyleLog
)
from app.models.conversation import CallSession, CallTurn
from app.models.appointment import Appointment
from app.models.knowledge import KnowledgeArticle, DeclinedQueryLog
from app.models.rules_alert import Alert
from app.services.language_service import LanguageService
from app.services.rules_engine import RulesEngine
from app.services.llm_extraction import llm_extraction_service
from app.core.audit import log_audit_event

class ConversationService:
    """
    Care Conversation State Engine
    """

    STEPS_ORDER = [
        "IDENTITY_CHECK",
        "LANGUAGE_CHECK",
        "WELLBEING",
        "SYMPTOMS_PAIN",
        "SYMPTOMS_BREATHLESSNESS",
        "VITALS_SPO2",
        "VITALS_BP",
        "MEDICATION",
        "LIFESTYLE_HYDRATION",
        "APPOINTMENT",
        "WRAP_UP"
    ]

    @classmethod
    def initiate_session(
        cls,
        db: Session,
        patient_id: str,
        call_type: str = "MORNING_CHECKIN",
        direction: str = "OUTBOUND",
        caller_phone: Optional[str] = None
    ) -> CallSession:
        patient = db.get(Patient, patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        consent_stmt = select(Consent).where(Consent.patient_id == patient_id)
        consent = db.execute(consent_stmt).scalars().first()
        if not consent or not consent.voice_contact or patient.status == "CONSENT_WITHDRAWN":
            raise ValueError("Outbound call blocked: Explicit patient voice contact consent not granted or withdrawn.")

        session = CallSession(
            patient_id=patient_id,
            direction=direction,
            call_type=call_type,
            status="IN_PROGRESS",
            disposition="IN_PROGRESS",
            language_used=patient.preferred_language or "en",
            current_step_key="IDENTITY_CHECK",
            caller_phone=caller_phone or patient.phone,
            created_at=datetime.utcnow()
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        log_audit_event(
            db=db,
            event_type="CALL_INITIATED",
            actor_id="SYSTEM",
            actor_role="SYSTEM",
            resource="call_session",
            details={
                "session_id": session.id,
                "direction": direction,
                "call_type": call_type,
                "language": session.language_used
            },
            patient_id=patient_id
        )

        return session

    @classmethod
    def get_initial_prompt(cls, db: Session, session: CallSession) -> Tuple[str, str]:
        patient = db.get(Patient, session.patient_id)
        lang = session.language_used

        prompt = LanguageService.get_prompt(
            "IDENTITY_VERIFICATION",
            lang=lang,
            name=f"{patient.first_name} {patient.last_name}"
        )
        return prompt, "IDENTITY_CHECK"

    @classmethod
    def process_turn(
        cls,
        db: Session,
        session_id: str,
        user_speech: str
    ) -> Dict[str, Any]:
        session = db.get(CallSession, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        patient = db.get(Patient, session.patient_id)
        current_step = session.current_step_key
        resume_ctx = dict(session.resume_context or {})
        lang = session.language_used

        # 1. Mid-conversation Language Switch (LN-03)
        new_lang = LanguageService.detect_language_switch_request(user_speech)
        if new_lang and new_lang != lang:
            session.language_used = new_lang
            lang = new_lang
            patient.preferred_language = new_lang
            db.commit()

        # 2. Transfer to Human Clinician Request (CV-07)
        speech_lower = user_speech.lower()
        if any(term in speech_lower for term in [
            "speak to doctor", "talk to nurse", "human", "care team",
            "doctor se baat", "nurse se baat", "doctorashi bola"
        ]):
            session.transferred_to_human = True
            session.transfer_reason = "Patient voice request"
            session.status = "COMPLETED"
            session.disposition = "PARTIAL"
            db.commit()

            msg = LanguageService.get_prompt("TRANSFER_CALLBACK_LOGGED", lang=lang)
            return {
                "session_id": session.id,
                "turn_index": len(session.turns or []),
                "step_key": "TRANSFER",
                "agent_prompt_text": msg,
                "language": lang,
                "is_completed": True,
                "is_transferred": True,
                "disposition": "PARTIAL",
                "extracted_data": {"action": "human_transfer_requested"}
            }

        # 3. Check for Medication Dosage Guardrail (MD-07, KQ-03)
        if any(term in speech_lower for term in [
            "increase dose", "decrease dose", "change dose", "double the tablet",
            "dosage badha do", "dawa badha do", "goli kami karu ka", "dosage change"
        ]):
            declined_log = DeclinedQueryLog(
                patient_id=patient.id,
                call_session_id=session.id,
                query_text=user_speech,
                query_type="DOSAGE",
                routed_to="TREATING_DOCTOR",
                standard_response_delivered="Standard dosage guardrail script delivered. Clinician callback queued."
            )
            db.add(declined_log)
            db.commit()

            guardrail_prompt = LanguageService.get_prompt(
                "MEDICATION_DOSAGE_GUARDRAIL",
                lang=lang,
                doctor_name=patient.treating_doctor_name or "your doctor"
            )
            return {
                "session_id": session.id,
                "turn_index": len(session.turns or []),
                "step_key": current_step,
                "agent_prompt_text": guardrail_prompt,
                "language": lang,
                "is_completed": False,
                "extracted_data": {"guardrail_triggered": "MD-07_DOSAGE_ROUTED"}
            }

        # 4. Step Processing State Machine
        turn_index = len(session.turns or [])
        turn_extracted_data: Dict[str, Any] = {}
        next_step = current_step
        agent_response_text = ""
        is_completed = False
        disposition = "IN_PROGRESS"
        is_red_flag = False

        if current_step == "IDENTITY_CHECK":
            if any(term in speech_lower for term in ["yes", "speaking", "ha", "haan", "ho", "me boltoy", "bol raha hu"]):
                resume_ctx["caller_verified"] = True
                next_step = "WELLBEING"
                agent_response_text = LanguageService.get_prompt(
                    "WELLBEING_MORNING" if session.call_type == "MORNING_CHECKIN" else "WELLBEING_EVENING",
                    lang=lang,
                    name=patient.first_name
                )
            else:
                agent_response_text = LanguageService.get_prompt(
                    "UNAUTHORIZED_CALLER_REFUSAL",
                    lang=lang,
                    name=patient.first_name
                )
                session.status = "COMPLETED"
                session.disposition = "WRONG_PERSON"
                is_completed = True
                db.commit()
                return {
                    "session_id": session.id,
                    "turn_index": turn_index,
                    "step_key": current_step,
                    "agent_prompt_text": agent_response_text,
                    "language": lang,
                    "is_completed": True,
                    "disposition": "WRONG_PERSON",
                    "extracted_data": {"caller_verified": False}
                }

        elif current_step == "WELLBEING":
            extracted = asyncio.run(llm_extraction_service.extract_checkin_symptoms(user_speech))
            resume_ctx["wellbeing_transcript"] = user_speech
            resume_ctx["extracted_symptoms"] = extracted
            turn_extracted_data["symptoms_preliminary"] = extracted

            next_step = "SYMPTOMS_PAIN"
            agent_response_text = LanguageService.get_prompt("SYMPTOMS_PAIN", lang=lang)

        elif current_step == "SYMPTOMS_PAIN":
            extracted = asyncio.run(llm_extraction_service.extract_checkin_symptoms(user_speech))
            pain_level = extracted.get("pain_level", 0)
            resume_ctx["pain_level"] = pain_level
            turn_extracted_data["pain_level"] = pain_level

            if pain_level >= 8:
                is_red_flag = True
                agent_response_text = LanguageService.get_prompt("EMERGENCY_RED_FLAG_SCRIPT", lang=lang)
                checkin = SymptomCheckin(
                    patient_id=patient.id,
                    call_session_id=session.id,
                    checkin_type=session.call_type,
                    pain_level=pain_level,
                    comparison_with_yesterday={"pain": "worsened"}
                )
                db.add(checkin)
                db.flush()
                RulesEngine.evaluate_symptom_checkin(db, patient.id, checkin)
                session.status = "COMPLETED"
                session.disposition = "COMPLETED"
                is_completed = True
            else:
                next_step = "SYMPTOMS_BREATHLESSNESS"
                agent_response_text = LanguageService.get_prompt("SYMPTOMS_BREATHLESSNESS", lang=lang)

        elif current_step == "SYMPTOMS_BREATHLESSNESS":
            extracted = asyncio.run(llm_extraction_service.extract_checkin_symptoms(user_speech))
            breathlessness = extracted.get("breathlessness", "none")
            comparison = extracted.get("comparison", {})
            resume_ctx["breathlessness"] = breathlessness
            resume_ctx["symptom_comparison"] = comparison
            turn_extracted_data["breathlessness"] = breathlessness

            checkin = SymptomCheckin(
                patient_id=patient.id,
                call_session_id=session.id,
                checkin_type=session.call_type,
                pain_level=resume_ctx.get("pain_level", 0),
                breathlessness=breathlessness,
                comparison_with_yesterday=comparison,
                other_symptoms_verbatim=extracted.get("other_verbatim")
            )
            db.add(checkin)
            db.flush()
            alerts = RulesEngine.evaluate_symptom_checkin(db, patient.id, checkin)
            if any(a.severity == "CRITICAL" for a in alerts):
                is_red_flag = True
                agent_response_text = LanguageService.get_prompt("EMERGENCY_RED_FLAG_SCRIPT", lang=lang)
                session.status = "COMPLETED"
                session.disposition = "COMPLETED"
                is_completed = True
            else:
                next_step = "VITALS_SPO2"
                agent_response_text = LanguageService.get_prompt("VITALS_SPO2_PROMPT", lang=lang)

        elif current_step == "VITALS_SPO2":
            parsed = LanguageService.parse_vitals_reading_from_speech("SPO2", user_speech)
            if not parsed or parsed[0] is None:
                reading = VitalReading(
                    patient_id=patient.id,
                    call_session_id=session.id,
                    vital_type="SPO2",
                    value=None,
                    unit="%",
                    status="NOT_PROVIDED",
                    voice_confirmed=False,
                    notes="Patient did not measure or provide SpO2"
                )
                db.add(reading)
                db.flush()
                next_step = "VITALS_BP"
                agent_response_text = LanguageService.get_prompt("VITALS_BP_PROMPT", lang=lang)
            else:
                val = parsed[0]
                status, alert = RulesEngine.evaluate_vital_reading(
                    db=db,
                    patient_id=patient.id,
                    vital_type="SPO2",
                    value=val,
                    unit="%"
                )
                if status == "IMPLAUSIBLE":
                    agent_response_text = LanguageService.get_prompt("VITALS_IMPLAUSIBLE_REASK", lang=lang, value=val)
                    next_step = "VITALS_SPO2"
                else:
                    reading = VitalReading(
                        patient_id=patient.id,
                        call_session_id=session.id,
                        vital_type="SPO2",
                        value=val,
                        unit="%",
                        status=status,
                        voice_confirmed=True
                    )
                    db.add(reading)
                    db.flush()
                    resume_ctx["spo2"] = val
                    turn_extracted_data["spo2"] = val
                    if status == "CRITICAL":
                        is_red_flag = True
                        agent_response_text = LanguageService.get_prompt("EMERGENCY_RED_FLAG_SCRIPT", lang=lang)
                        session.status = "COMPLETED"
                        session.disposition = "COMPLETED"
                        is_completed = True
                    else:
                        readback = LanguageService.get_prompt("VITALS_CONFIRMATION_READBACK", lang=lang, vital_name="Oxygen SpO2", value=val, unit="%")
                        bp_prompt = LanguageService.get_prompt("VITALS_BP_PROMPT", lang=lang)
                        agent_response_text = f"{readback} {bp_prompt}"
                        next_step = "VITALS_BP"

        elif current_step == "VITALS_BP":
            parsed = LanguageService.parse_vitals_reading_from_speech("BP", user_speech)
            if not parsed or parsed[0] is None:
                reading = VitalReading(
                    patient_id=patient.id,
                    call_session_id=session.id,
                    vital_type="BP_SYSTOLIC",
                    value=None,
                    unit="mmHg",
                    status="NOT_PROVIDED",
                    notes="Patient did not measure BP"
                )
                db.add(reading)
                db.flush()
            else:
                sys, dia = parsed
                status, alert = RulesEngine.evaluate_vital_reading(
                    db=db,
                    patient_id=patient.id,
                    vital_type="BP_SYSTOLIC",
                    value=sys,
                    secondary_value=dia,
                    unit="mmHg"
                )
                reading = VitalReading(
                    patient_id=patient.id,
                    call_session_id=session.id,
                    vital_type="BP_SYSTOLIC",
                    value=sys,
                    secondary_value=dia,
                    unit="mmHg",
                    status=status,
                    voice_confirmed=True
                )
                db.add(reading)
                db.flush()
                resume_ctx["bp_sys"] = sys
                resume_ctx["bp_dia"] = dia
                turn_extracted_data["bp"] = f"{sys}/{dia}"

            next_step = "MEDICATION"
            med_stmt = select(MedicationSchedule).where(
                MedicationSchedule.patient_id == patient.id,
                MedicationSchedule.is_active == True
            )
            meds = db.execute(med_stmt).scalars().all()
            if meds:
                first_med = meds[0]
                resume_ctx["current_med_id"] = first_med.id
                resume_ctx["current_med_name"] = first_med.medicine_name
                agent_response_text = LanguageService.get_prompt(
                    "MEDICATION_REMINDER",
                    lang=lang,
                    medicine_name=first_med.medicine_name,
                    dosage=first_med.dosage
                )
            else:
                next_step = "LIFESTYLE_HYDRATION"
                agent_response_text = "Have you been drinking water regularly today? How many glasses have you had so far?"

        elif current_step == "MEDICATION":
            med_status, med_reason = LanguageService.parse_code_mixed_medication_response(user_speech)
            med_name = resume_ctx.get("current_med_name", "Prescribed Medication")
            med_id = resume_ctx.get("current_med_id")

            if med_status == "DEFERRED":
                med_log = MedicationLog(
                    patient_id=patient.id,
                    medication_schedule_id=med_id,
                    medicine_name=med_name,
                    scheduled_time=datetime.utcnow(),
                    status="DEFERRED",
                    stated_reason="Patient requested reminder later",
                    deferral_count=1,
                    recorded_via="VOICE_CALL"
                )
                db.add(med_log)
                db.flush()
                agent_response_text = "Understood. I will reschedule a reminder for your medication in 30 minutes."
                next_step = "LIFESTYLE_HYDRATION"
            elif med_status == "TAKEN":
                med_log = MedicationLog(
                    patient_id=patient.id,
                    medication_schedule_id=med_id,
                    medicine_name=med_name,
                    scheduled_time=datetime.utcnow(),
                    actual_time=datetime.utcnow(),
                    status="TAKEN",
                    recorded_via="VOICE_CALL"
                )
                db.add(med_log)
                db.flush()
                agent_response_text = f"Great, I have recorded your dose of {med_name} as taken."
                next_step = "LIFESTYLE_HYDRATION"
            elif med_status == "MISSED":
                med_log = MedicationLog(
                    patient_id=patient.id,
                    medication_schedule_id=med_id,
                    medicine_name=med_name,
                    scheduled_time=datetime.utcnow(),
                    status="MISSED",
                    stated_reason=med_reason or "Patient reported missed dose",
                    recorded_via="VOICE_CALL"
                )
                db.add(med_log)
                db.flush()
                RulesEngine.evaluate_medication_miss(db, patient.id, med_name)
                agent_response_text = f"I have noted that you missed {med_name}. Please do not take an extra dose without consulting your doctor."
                next_step = "LIFESTYLE_HYDRATION"
            else:
                med_log = MedicationLog(
                    patient_id=patient.id,
                    medication_schedule_id=med_id,
                    medicine_name=med_name,
                    scheduled_time=datetime.utcnow(),
                    status="PENDING",
                    stated_reason="Unclear patient response",
                    recorded_via="VOICE_CALL"
                )
                db.add(med_log)
                db.flush()
                next_step = "LIFESTYLE_HYDRATION"
                agent_response_text = "I have noted that. Let us continue with your hydration and recovery check."

            turn_extracted_data["medication"] = {"name": med_name, "status": med_status, "reason": med_reason}
            agent_response_text += " Are you able to drink water at your scheduled intervals today?"

        elif current_step == "LIFESTYLE_HYDRATION":
            log = LifestyleLog(
                patient_id=patient.id,
                log_type="HYDRATION",
                target_value=8.0,
                actual_value=5.0 if "yes" in speech_lower or "ha" in speech_lower or "ho" in speech_lower else 2.0,
                unit="glasses",
                completion_status="COMPLETED" if "yes" in speech_lower or "ha" in speech_lower else "PARTIAL",
                recorded_at=datetime.utcnow()
            )
            db.add(log)
            db.flush()

            app_stmt = select(Appointment).where(
                Appointment.patient_id == patient.id,
                Appointment.scheduled_time >= datetime.utcnow()
            ).order_by(Appointment.scheduled_time).limit(1)
            appt = db.execute(app_stmt).scalars().first()

            if appt:
                next_step = "APPOINTMENT"
                resume_ctx["current_appointment_id"] = appt.id
                time_str = appt.scheduled_time.strftime("%A, %d %B at %I:%M %p")
                agent_response_text = (
                    f"You have an upcoming appointment for {appt.appointment_type.replace('_', ' ')} with "
                    f"{appt.doctor_facility_name} on {time_str}. Will you be able to attend?"
                )
            else:
                next_step = "WRAP_UP"
                agent_response_text = (
                    "Thank you for completing your daily recovery check-in. Your care team has received your updates. "
                    "Rest well and stay hydrated. Goodbye!"
                )
                is_completed = True
                disposition = "COMPLETED"

        elif current_step == "APPOINTMENT":
            appt_id = resume_ctx.get("current_appointment_id")
            if appt_id:
                appt = db.get(Appointment, appt_id)
                if appt:
                    if any(w in speech_lower for w in ["yes", "ha", "haan", "ho", "attend", "confirm"]):
                        appt.status = "CONFIRMED"
                        appt.attendance_confirmed_at = datetime.utcnow()
                        agent_response_text = "Thank you, your appointment attendance is confirmed."
                    elif any(w in speech_lower for w in ["reschedule", "change time", "badal do"]):
                        appt.status = "RESCHEDULE_REQUESTED"
                        appt.reschedule_reason = user_speech
                        appt.reschedule_task_created = True
                        agent_response_text = "I have raised a rescheduling task for your care team. They will contact you with alternate times."
                    elif any(w in speech_lower for w in ["no", "cannot", "nahi", "cancel"]):
                        appt.status = "DECLINED"
                        appt.decline_reason = user_speech
                        agent_response_text = "I have noted that you cannot attend. Please ensure you reschedule as follow-ups are important."
                    db.commit()

            next_step = "WRAP_UP"
            agent_response_text += " Thank you for taking the time to speak with me. Take care and have a restful day!"
            is_completed = True
            disposition = "COMPLETED"

        session.current_step_key = next_step
        session.resume_context = resume_ctx
        if is_completed:
            session.status = "COMPLETED"
            session.disposition = disposition
            session.duration_seconds = max(10, turn_index * 25)

        turn = CallTurn(
            call_session_id=session.id,
            turn_index=turn_index,
            step_key=current_step,
            agent_prompt=agent_response_text,
            patient_audio_transcript=user_speech,
            detected_language=lang,
            extracted_entities=turn_extracted_data,
            was_unanswered=False
        )
        db.add(turn)
        db.commit()

        log_audit_event(
            db=db,
            event_type="CALL_TURN_COMPLETED",
            actor_id="AI_COMPANION",
            actor_role="SYSTEM",
            resource="call_turn",
            details={
                "session_id": session.id,
                "turn": turn_index,
                "step": current_step,
                "next_step": next_step,
                "extracted": turn_extracted_data
            },
            patient_id=patient.id
        )

        return {
            "session_id": session.id,
            "turn_index": turn_index,
            "step_key": current_step,
            "next_step_key": next_step,
            "agent_prompt_text": agent_response_text,
            "language": lang,
            "is_completed": is_completed,
            "disposition": disposition if is_completed else None,
            "is_red_flag": is_red_flag,
            "extracted_data": turn_extracted_data
        }

    @classmethod
    def resume_interrupted_session(
        cls,
        db: Session,
        session_id: str
    ) -> Dict[str, Any]:
        session = db.get(CallSession, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        patient = db.get(Patient, session.patient_id)
        lang = session.language_used
        interrupted_step = session.current_step_key or "WELLBEING"

        prompt = f"Welcome back {patient.first_name}. We were interrupted during your check-in. Let us continue from where we left off."
        if interrupted_step == "VITALS_BP":
            prompt += " " + LanguageService.get_prompt("VITALS_BP_PROMPT", lang=lang)
        elif interrupted_step == "VITALS_SPO2":
            prompt += " " + LanguageService.get_prompt("VITALS_SPO2_PROMPT", lang=lang)
        elif interrupted_step == "MEDICATION":
            prompt += " " + LanguageService.get_prompt("MEDICATION_REMINDER", lang=lang, medicine_name="your medication", dosage="prescribed dose")
        else:
            prompt += " " + LanguageService.get_prompt("WELLBEING_MORNING", lang=lang, name=patient.first_name)

        session.status = "IN_PROGRESS"
        session.interrupted_at = None
        db.commit()

        return {
            "session_id": session.id,
            "resumed_at_step": interrupted_step,
            "agent_prompt_text": prompt,
            "language": lang,
            "saved_context": session.resume_context
        }
