import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import List
from sqlalchemy import select, and_, or_, desc
from app.core.database import AsyncSessionLocal
from app.models.patient import Patient, Consent, Caregiver
from app.models.conversation import CallSession
from app.models.rules_alert import Alert, AlertActionLog
from app.models.clinical import MedicationSchedule, MedicationLog
from app.services.rules_engine import RulesEngine
from app.services.conversation_service import ConversationService
from app.services.progress_service import ProgressService
from app.services.telephony.twilio_adapter import TwilioCallChannel
from app.core.config import settings

logger = logging.getLogger("background-worker")

twilio_channel = TwilioCallChannel()

async def process_scheduled_outbound_calls():
    """
    CV-01, CI-01, CI-07: Scan active patients for morning and evening scheduled calls.
    Checks consent and honors DND hours (CM-06).
    """
    now = datetime.utcnow()
    current_time_str = now.strftime("%H:%M")

    async with AsyncSessionLocal() as db:
        # Fetch active patients
        stmt = select(Patient).where(Patient.status == "ACTIVE")
        patients = (await db.execute(stmt)).scalars().all()

        for patient in patients:
            # 1. Verify Consent (ON-04, ON-06, PL-03)
            consent_stmt = select(Consent).where(Consent.patient_id == patient.id)
            consent = (await db.execute(consent_stmt)).scalars().first()
            if not consent or not consent.voice_contact:
                continue

            # 2. Check if already called today for morning/evening
            today_start = datetime.combine(date.today(), datetime.min.time())
            call_stmt = select(CallSession).where(
                CallSession.patient_id == patient.id,
                CallSession.created_at >= today_start
            )
            calls_today = (await db.execute(call_stmt)).scalars().all()

            # Check morning checkin schedule
            needs_morning = not any(c.call_type == "MORNING_CHECKIN" and c.disposition == "COMPLETED" for c in calls_today)
            if needs_morning:
                try:
                    logger.info(f"Worker: Launching scheduled morning call for patient {patient.id} ({patient.first_name})")
                    session = await ConversationService.initiate_session(
                        db=db,
                        patient_id=patient.id,
                        call_type="MORNING_CHECKIN",
                        direction="OUTBOUND"
                    )
                    # Trigger call via configured channel
                    await twilio_channel.initiate_outbound_call(
                        to_phone=patient.phone,
                        session_id=session.id,
                        webhook_url=settings.TWILIO_WEBHOOK_URL,
                        language=session.language_used
                    )
                except Exception as e:
                    logger.error(f"Error initiating scheduled call for {patient.id}: {e}")

async def process_failed_call_retries():
    """
    CM-01, CM-02: Retry unsuccessful calls after retry interval up to retry limit.
    Escalate to caregiver and care team once configured contact attempts are exhausted.
    """
    async with AsyncSessionLocal() as db:
        # Find failed sessions from past 24 hours that haven't been completed yet
        cutoff = datetime.utcnow() - timedelta(minutes=settings.RETRY_INTERVAL_MINUTES)
        stmt = select(CallSession).where(
            CallSession.status == "FAILED",
            CallSession.disposition.in_(["NO_ANSWER", "BUSY", "UNREACHABLE"]),
            CallSession.updated_at <= cutoff
        ).order_by(CallSession.updated_at)
        failed_sessions = (await db.execute(stmt)).scalars().all()

        for session in failed_sessions:
            patient = await db.get(Patient, session.patient_id)
            if not patient or patient.status != "ACTIVE":
                continue

            if session.retry_count < patient.retry_limit:
                logger.info(f"Worker: Retrying call for patient {patient.id} (Attempt {session.retry_count + 1}/{patient.retry_limit})")
                session.retry_count += 1
                session.status = "IN_PROGRESS"
                session.updated_at = datetime.utcnow()
                await db.commit()

                try:
                    await twilio_channel.initiate_outbound_call(
                        to_phone=patient.phone,
                        session_id=session.id,
                        webhook_url=settings.TWILIO_WEBHOOK_URL,
                        language=session.language_used
                    )
                except Exception as ex:
                    logger.error(f"Worker retry error: {ex}")
            else:
                # Attempts exhausted -> Escalate to caregiver and care team (CM-02)
                logger.warning(f"Worker: Contact attempts exhausted for patient {patient.id}. Escalating to care team.")
                await RulesEngine.evaluate_contact_failure(
                    db=db,
                    patient_id=patient.id,
                    retry_count=session.retry_count,
                    retry_limit=patient.retry_limit,
                    last_disposition=session.disposition
                )
                session.status = "ESCALATED"
                await db.commit()

async def process_alert_sla_monitor():
    """
    ES-06, ES-07: Monitor SLA due times for open alerts.
    If unacknowledged when SLA expires, escalate to next contact in escalation hierarchy.
    """
    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()
        stmt = select(Alert).where(
            Alert.status == "OPEN",
            Alert.sla_due_at <= now
        )
        breached_alerts = (await db.execute(stmt)).scalars().all()

        for alert in breached_alerts:
            logger.warning(f"Worker: Alert {alert.id} ({alert.rule_code}) breached SLA! Auto-escalating.")
            alert.status = "ESCALATED"
            
            action_log = AlertActionLog(
                alert_id=alert.id,
                user_id="BACKGROUND_WORKER",
                user_name="Alert SLA Monitor Worker",
                action="ESCALATED",
                notes=f"Auto-escalated to senior clinical on-call: SLA expired at {alert.sla_due_at.isoformat()}"
            )
            db.add(action_log)
            await db.commit()

async def process_daily_progress_and_summaries():
    """
    PR-01, PR-02, PR-03: Calculate daily Care Progress score and deliver EOD summaries.
    """
    async with AsyncSessionLocal() as db:
        stmt = select(Patient).where(Patient.status == "ACTIVE")
        patients = (await db.execute(stmt)).scalars().all()

        for patient in patients:
            try:
                # 1. Calculate Score
                await ProgressService.calculate_daily_progress_score(db, patient.id)
                # 2. Voice summary
                await ProgressService.generate_end_of_day_voice_summary(db, patient.id)
                # 3. Caregiver summary
                await ProgressService.generate_caregiver_summary(db, patient.id)
                # 4. Check composite decline pattern across indicators (ES-08)
                await RulesEngine.evaluate_composite_decline(db, patient.id)
            except Exception as e:
                logger.error(f"Error computing daily progress for {patient.id}: {e}")
