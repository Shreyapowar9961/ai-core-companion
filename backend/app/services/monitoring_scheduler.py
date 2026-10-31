import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from app.core.database import SessionLocal
from app.models.patient import Patient
from app.models.clinical import MedicationSchedule, MedicationLog
from app.models.monitoring import MonitoringPlan, CheckinTask, CommunicationLog
from app.models.rules_alert import Alert
from app.core.audit import log_audit_event

logger = logging.getLogger("monitoring-scheduler")

class BackgroundMonitoringScheduler:
    """
    Phase 3 & 5: Persistent, database-backed automated monitoring and communication scheduler.
    Recovers cleanly after backend restart.
    Strictly ₹0 local honest simulation with duplicate prevention.
    """
    _is_running = False
    _task = None

    @classmethod
    def start(cls):
        if cls._is_running:
            return
        cls._is_running = True
        cls._task = asyncio.create_task(cls._loop())
        logger.info("Background Monitoring Scheduler started.")

    @classmethod
    def stop(cls):
        cls._is_running = False
        if cls._task:
            cls._task.cancel()
        logger.info("Background Monitoring Scheduler stopped.")

    @classmethod
    async def _loop(cls):
        # Give lifespan 3 seconds to complete table creation and migrations on startup
        await asyncio.sleep(3)
        while cls._is_running:
            try:
                # Run monitoring cycle
                cls.run_cycle()
            except Exception as e:
                logger.error(f"Error in monitoring scheduler cycle: {e}")
            # Wait 60 seconds between cycles
            await asyncio.sleep(60)

    @classmethod
    def run_cycle(cls, db: Session = None) -> Dict[str, Any]:
        """
        Executes a single scheduler cycle.
        Can be called by background task or triggered directly via API for instant testing/demos.
        """
        owns_session = False
        if db is None:
            db = SessionLocal()
            owns_session = True

        tasks_created = 0
        reminders_created = 0
        unanswered_flagged = 0

        try:
            now = datetime.utcnow()
            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())

            # -------------------------------------------------------------
            # 1. GENERATE SCHEDULED CHECK-IN TASKS & COMMUNICATIONS
            # -------------------------------------------------------------
            active_plans = db.execute(
                select(MonitoringPlan).where(
                    MonitoringPlan.is_active == True,
                    MonitoringPlan.start_date <= today,
                    MonitoringPlan.end_date >= today
                )
            ).scalars().all()

            for plan in active_plans:
                patient = db.get(Patient, plan.patient_id)
                if not patient or patient.status != "ACTIVE":
                    continue

                # Duplicate Prevention: Check if task already exists for today
                existing_task = db.execute(
                    select(CheckinTask).where(
                        CheckinTask.patient_id == patient.id,
                        CheckinTask.scheduled_for >= today_start
                    )
                ).scalars().first()

                if not existing_task:
                    # Create new CheckinTask
                    task = CheckinTask(
                        monitoring_plan_id=plan.id,
                        patient_id=patient.id,
                        scheduled_for=now,
                        status="PENDING",
                        channel=plan.communication_channel,
                        category="ROUTINE",
                        category_reason="Scheduled daily recovery check-in generated."
                    )
                    db.add(task)
                    tasks_created += 1

                    # Create honest simulated communication task
                    sim_channel = f"SIMULATED_{plan.communication_channel.upper()}"
                    comm = CommunicationLog(
                        patient_id=patient.id,
                        channel=sim_channel,
                        message_type="RECOVERY_CHECKIN",
                        recipient_phone=patient.phone,
                        content=f"Apex Heart Institute: Namaste {patient.first_name}. Your scheduled recovery check-in is now ready. Please open your patient portal to report today's vitals and symptoms.",
                        status="DELIVERED",
                        is_simulated=True
                    )
                    db.add(comm)

            # -------------------------------------------------------------
            # 2. GENERATE MEDICATION REMINDERS
            # -------------------------------------------------------------
            active_meds = db.execute(
                select(MedicationSchedule).where(
                    MedicationSchedule.is_active == True
                )
            ).scalars().all()

            for med in active_meds:
                patient = db.get(Patient, med.patient_id)
                if not patient or patient.status != "ACTIVE":
                    continue

                # Check if medication log exists for today
                existing_log = db.execute(
                    select(MedicationLog).where(
                        MedicationLog.patient_id == med.patient_id,
                        MedicationLog.medication_schedule_id == med.id,
                        MedicationLog.scheduled_time >= today_start
                    )
                ).scalars().first()

                if not existing_log:
                    # Check if a reminder communication was already sent in the last 4 hours
                    four_hours_ago = now - timedelta(hours=4)
                    recent_reminder = db.execute(
                        select(CommunicationLog).where(
                            CommunicationLog.patient_id == med.patient_id,
                            CommunicationLog.message_type == "MEDICATION_REMINDER",
                            CommunicationLog.sent_at >= four_hours_ago
                        )
                    ).scalars().first()

                    if not recent_reminder:
                        rem_comm = CommunicationLog(
                            patient_id=med.patient_id,
                            channel="SIMULATED_WHATSAPP",
                            message_type="MEDICATION_REMINDER",
                            recipient_phone=patient.phone,
                            content=f"Medication Reminder: Time to take your {med.medicine_name} ({med.dosage}). Instructions: {med.instructions or 'Take with water'}. Please confirm in your portal.",
                            status="DELIVERED",
                            is_simulated=True
                        )
                        db.add(rem_comm)
                        reminders_created += 1

            # -------------------------------------------------------------
            # 3. DETECT UNANSWERED CHECK-INS & AUTO-CATEGORISE
            # -------------------------------------------------------------
            stale_threshold = now - timedelta(hours=18)
            stale_tasks = db.execute(
                select(CheckinTask).where(
                    CheckinTask.status == "PENDING",
                    CheckinTask.scheduled_for <= stale_threshold
                )
            ).scalars().all()

            for st in stale_tasks:
                st.status = "EXPIRED"
                st.category = "UNANSWERED"
                st.category_reason = "Check-in window expired without patient submission."
                unanswered_flagged += 1

                # Generate Alert for clinician review if unanswered
                alert = Alert(
                    patient_id=st.patient_id,
                    rule_code="UNANSWERED_CHECKIN",
                    severity="MEDIUM",
                    title="Missed Daily Recovery Check-in",
                    description=f"Patient missed scheduled recovery check-in from {st.scheduled_for.strftime('%d-%b %H:%M')}.",
                    supporting_data={"task_id": st.id},
                    status="OPEN",
                    sla_due_at=now + timedelta(hours=4)
                )
                db.add(alert)
                db.flush()
                st.alert_id = alert.id

            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"Error executing monitoring cycle: {e}")
            raise e
        finally:
            if owns_session:
                db.close()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "tasks_created": tasks_created,
            "reminders_created": reminders_created,
            "unanswered_flagged": unanswered_flagged
        }
