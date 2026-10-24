import pytest
import asyncio
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from app.core.database import Base
from app.models.patient import Patient
from app.models.clinical import SymptomCheckin, MedicationLog
from app.models.rules_alert import Alert
from app.services.rules_engine import RulesEngine

async def setup_test_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    session = session_maker()
    p = Patient(
        id="test-pt-1",
        first_name="Anil",
        last_name="Kumble",
        dob=date(1960, 1, 1),
        gender="Male",
        phone="+919999900000",
        diagnosis="Post-Angioplasty",
        discharge_date=date.today(),
        status="ACTIVE"
    )
    session.add(p)
    await session.commit()
    return engine, session

def test_deterministic_vitals_critical_threshold():
    """
    Mandate: All escalation logic runs in a deterministic rules engine - NEVER in the LLM.
    VT-03, VT-04, ES-01: Critical SpO2 < 88% must trigger Critical alert with 15-min SLA.
    """
    async def _run():
        engine, db = await setup_test_db()
        try:
            status, alert = await RulesEngine.evaluate_vital_reading(
                db=db,
                patient_id="test-pt-1",
                vital_type="SPO2",
                value=86.0,
                unit="%"
            )
            assert status == "CRITICAL"
            assert alert is not None
            assert alert.severity == "CRITICAL"
            assert alert.rule_code == "RULE_VITAL_SPO2_CRITICAL"
            assert "86.0 %" in alert.title
            sla_diff = (alert.sla_due_at - datetime.utcnow()).total_seconds()
            assert 800 <= sla_diff <= 950
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(_run())

def test_vitals_plausibility_check():
    """
    VT-02: Validate values against plausible ranges and reject implausible readings.
    """
    async def _run():
        engine, db = await setup_test_db()
        try:
            status, alert = await RulesEngine.evaluate_vital_reading(
                db=db,
                patient_id="test-pt-1",
                vital_type="SPO2",
                value=150.0,
                unit="%"
            )
            assert status == "IMPLAUSIBLE"
            assert alert is None
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(_run())

def test_red_flag_acute_symptom_emergency():
    """
    ES-03: On red-flag presentation (severe acute pain >= 8), deliver emergency script
    and raise critical alert.
    """
    async def _run():
        engine, db = await setup_test_db()
        try:
            checkin = SymptomCheckin(
                patient_id="test-pt-1",
                pain_level=9,
                breathlessness="none",
                comparison_with_yesterday={"pain": "worsened"}
            )
            db.add(checkin)
            await db.flush()

            alerts = await RulesEngine.evaluate_symptom_checkin(db, "test-pt-1", checkin)
            assert len(alerts) >= 1
            assert any(a.severity == "CRITICAL" and a.rule_code == "RULE_RED_FLAG_EMERGENCY" for a in alerts)
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(_run())

def test_sustained_worsening_trend():
    """
    CI-05: Detect sustained worsening trend across consecutive checkins and invoke escalation rule.
    """
    async def _run():
        engine, db = await setup_test_db()
        try:
            c1 = SymptomCheckin(
                patient_id="test-pt-1",
                recorded_at=datetime.utcnow() - timedelta(days=1),
                breathlessness="moderate",
                comparison_with_yesterday={"breathlessness": "worsened"}
            )
            db.add(c1)
            await db.commit()

            c2 = SymptomCheckin(
                patient_id="test-pt-1",
                recorded_at=datetime.utcnow(),
                breathlessness="moderate",
                comparison_with_yesterday={"breathlessness": "worsened"}
            )
            db.add(c2)
            await db.flush()

            alerts = await RulesEngine.evaluate_symptom_checkin(db, "test-pt-1", c2)
            assert any(a.rule_code == "RULE_SYMPTOM_SUSTAINED_WORSENING_BREATHLESSNESS" for a in alerts)
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(_run())

def test_medication_repeated_miss_escalation():
    """
    MD-05: Detect repeated misses against threshold (>=2 doses) and trigger escalation.
    """
    async def _run():
        engine, db = await setup_test_db()
        try:
            m1 = MedicationLog(
                patient_id="test-pt-1",
                medicine_name="Amlodipine",
                scheduled_time=datetime.utcnow() - timedelta(days=1),
                status="MISSED",
                stated_reason="Forgot"
            )
            m2 = MedicationLog(
                patient_id="test-pt-1",
                medicine_name="Amlodipine",
                scheduled_time=datetime.utcnow(),
                status="MISSED",
                stated_reason="Side effects"
            )
            db.add_all([m1, m2])
            await db.commit()

            alert = await RulesEngine.evaluate_medication_miss(db, "test-pt-1", "Amlodipine")
            assert alert is not None
            assert alert.rule_code == "RULE_MED_REPEATED_MISS"
            assert alert.severity == "HIGH"
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(_run())
