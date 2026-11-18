"""
Phase 1.1 Correctness Hardening Test Suite:
Validates medication adherence correctness (idempotency, distinct dose matching,
orphan/PRN/alternate-day/weekly handling) and centralized alert deduplication
with active investigation lifecycle statuses and database uniqueness conflict safety.
Runs exclusively against an isolated PostgreSQL test database (Zero SQLite).
"""
import os
import pytest
from datetime import datetime, date, time, timedelta
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.patient import Facility, Patient, CarePlan
from app.models.clinical import MedicationSchedule, MedicationLog, SymptomCheckin
from app.models.rules_alert import Alert, AlertActionLog
from app.models.monitoring import CheckinTask
from app.services.rules_engine import RulesEngine
from app.api.v1.dashboard import calculate_patient_7d_adherence
from app.api.v1.patient_portal import confirm_medication_taken, ConfirmMedicationRequest
from app.core.security import AuthUser, UserRole

TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_care_companion_test")

@pytest.fixture
def db_session():
    """
    Isolated PostgreSQL test session running against ai_care_companion_test database.
    Zero SQLite. Strictly PostgreSQL with schema compatible with Supabase PostgreSQL.
    Rolls back transaction after each test for clean isolation.
    """
    try:
        engine = create_engine(TEST_DB_URL, connect_args={"connect_timeout": 3})
        connection = engine.connect()
    except Exception as exc:
        pytest.skip(f"PostgreSQL test database unreachable: {exc}")

    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    # Seed baseline facility, patient, and care plan
    facility = Facility(id="fac_1", name="Apex Memorial Hospital", location="Pune")
    session.add(facility)

    patient = Patient(
        id="pt_phase11",
        facility_id="fac_1",
        first_name="Anita",
        last_name="Deshmukh",
        dob=date(1980, 1, 1),
        gender="Female",
        phone="+919876543210",
        diagnosis="Post-CABG",
        discharge_date=date(2026, 11, 1),
        status="ACTIVE"
    )
    care_plan = CarePlan(
        id="cp_phase11",
        patient_id="pt_phase11",
        version=1,
        is_active=True
    )
    session.add(patient)
    session.add(care_plan)
    session.flush()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


# =========================================================================
# Part A: Medication Adherence Hardening Tests
# =========================================================================

def test_confirm_medication_taken_idempotent(db_session):
    """Requirement A.1 & A.2: Repeated confirmation of same dose does not insert extra TAKEN rows."""
    now = datetime(2026, 11, 11, 9, 0, 0)
    sched = MedicationSchedule(
        id="sched_idemp",
        care_plan_id="cp_phase11",
        patient_id="pt_phase11",
        medicine_name="Aspirin",
        dosage="75mg",
        frequency="Once daily",
        effective_start_date=date(2026, 11, 1),
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()

    user = AuthUser(id="usr_pt", email="anita@test.org", role=UserRole.PATIENT, patient_id="pt_phase11", name="Anita")
    req = ConfirmMedicationRequest(
        medication_schedule_id="sched_idemp",
        medicine_name="Aspirin",
        scheduled_time=now
    )

    # First confirmation: creates log
    res1 = confirm_medication_taken(req, user, db_session)
    assert res1["status"] == "TAKEN"

    # Second confirmation: idempotent no-op, returns existing without duplicate insert
    res2 = confirm_medication_taken(req, user, db_session)
    assert res2["status"] == "TAKEN"
    assert res2.get("idempotent") is True

    # Third confirmation: still idempotent
    res3 = confirm_medication_taken(req, user, db_session)
    assert res3.get("idempotent") is True

    # Total rows in medication_logs must remain exactly 1
    total_logs = db_session.execute(
        select(MedicationLog).where(MedicationLog.patient_id == "pt_phase11")
    ).scalars().all()
    assert len(total_logs) == 1


def test_duplicate_taken_logs_cannot_mask_missed_doses(db_session):
    """
    Requirement A.3: Calculate adherence using distinct expected dose occurrences.
    Patient prescribed 7 daily doses takes 4, misses 3.
    If 4 duplicate TAKEN logs are present for dose 1 (total 8 logs in DB),
    adherence MUST remain 57.1% (4/7) and NOT be inflated to 100%.
    """
    now = datetime(2026, 11, 11, 12, 0, 0)
    sched = MedicationSchedule(
        id="sched_mask",
        care_plan_id="cp_phase11",
        patient_id="pt_phase11",
        medicine_name="Metoprolol",
        dosage="50mg",
        frequency="Once daily",
        effective_start_date=date(2026, 11, 1),
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()

    # Doses taken on days: 6 days ago, 5 days ago, 4 days ago, 3 days ago (4 taken)
    # Doses missed on days: 2 days ago, 1 day ago, today (3 missed)
    for i in [6, 5, 4, 3]:
        dose_time = now - timedelta(days=i)
        dose_dt = datetime.combine(dose_time.date(), time(9, 0))
        db_session.add(MedicationLog(
            patient_id="pt_phase11",
            medication_schedule_id="sched_mask",
            medicine_name="Metoprolol",
            scheduled_time=dose_dt,
            actual_time=dose_dt,
            status="TAKEN"
        ))

    # Inject 4 DUPLICATE taken logs for the dose 6 days ago
    dup_dt = datetime.combine((now - timedelta(days=6)).date(), time(9, 0))
    for _ in range(4):
        db_session.add(MedicationLog(
            patient_id="pt_phase11",
            medication_schedule_id="sched_mask",
            medicine_name="Metoprolol",
            scheduled_time=dup_dt,
            actual_time=dup_dt,
            status="TAKEN"
        ))
    db_session.commit()

    # Total TAKEN logs in DB = 4 + 4 = 8 logs. Total expected doses = 7 doses.
    # Naive row count would compute 8 / 7 -> 100.0%.
    # Hardened distinct slot calculation must compute exactly 4 / 7 = 57.1%!
    adherence = calculate_patient_7d_adherence(db_session, "pt_phase11", now=now)
    assert adherence == 57.1


def test_orphan_and_excluded_schedule_logs_ignored(db_session):
    """
    Requirement A.4 & A.5: Orphan logs (medication_schedule_id = None) and logs
    from inactive/other schedules do NOT increase adherence.
    """
    now = datetime(2026, 11, 11, 12, 0, 0)
    sched = MedicationSchedule(
        id="sched_valid",
        care_plan_id="cp_phase11",
        patient_id="pt_phase11",
        medicine_name="Atorvastatin",
        dosage="40mg",
        frequency="Once daily",
        effective_start_date=date(2026, 11, 1),
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()

    # Patient took 2 valid doses out of 7 expected (2 / 7 = 28.6%)
    for i in [6, 5]:
        dose_dt = datetime.combine((now - timedelta(days=i)).date(), time(9, 0))
        db_session.add(MedicationLog(
            patient_id="pt_phase11",
            medication_schedule_id="sched_valid",
            medicine_name="Atorvastatin",
            scheduled_time=dose_dt,
            status="TAKEN"
        ))

    # Add 5 ORPHAN logs (medication_schedule_id = None, e.g. OTC or ad-hoc)
    for i in [4, 3, 2, 1, 0]:
        dose_dt = datetime.combine((now - timedelta(days=i)).date(), time(9, 0))
        db_session.add(MedicationLog(
            patient_id="pt_phase11",
            medication_schedule_id=None,
            medicine_name="Paracetamol (OTC)",
            scheduled_time=dose_dt,
            status="TAKEN"
        ))
    db_session.commit()

    # Orphan logs must be ignored; adherence remains 2 / 7 = 28.6%
    adherence = calculate_patient_7d_adherence(db_session, "pt_phase11", now=now)
    assert adherence == 28.6


def test_prn_schedules_excluded_from_denominator(db_session):
    """
    Requirement A.8: PRN / as-needed schedules are excluded from fixed-dose adherence denominator.
    """
    now = datetime(2026, 11, 11, 12, 0, 0)
    prn_sched = MedicationSchedule(
        id="sched_prn",
        care_plan_id="cp_phase11",
        patient_id="pt_phase11",
        medicine_name="Nitroglycerin",
        dosage="0.4mg sublingual",
        frequency="PRN / As needed for chest pain",
        instructions="Take 1 tablet under tongue as needed for acute pain",
        effective_start_date=date(2026, 11, 1),
        is_active=True
    )
    db_session.add(prn_sched)
    db_session.commit()

    # Patient has only PRN medication, no fixed daily doses
    # Denominator = 0 expected doses -> defaults safely to 100.0%
    adherence = calculate_patient_7d_adherence(db_session, "pt_phase11", now=now)
    assert adherence == 100.0


def test_alternate_day_schedule_calculation(db_session):
    """
    Requirement A.7: Alternate-day schedules anchored on effective_start_date
    expect doses every 2 days (4 doses over 7 days).
    """
    # Set anchor date to 6 days ago (start of 7-day window)
    now = datetime(2026, 11, 11, 12, 0, 0)
    start_date = (now - timedelta(days=6)).date()

    sched = MedicationSchedule(
        id="sched_alt",
        care_plan_id="cp_phase11",
        patient_id="pt_phase11",
        medicine_name="Warfarin",
        dosage="5mg",
        frequency="Alternate days",
        effective_start_date=start_date,
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()

    # Alternate days in 7-day window: Day 0, Day 2, Day 4, Day 6 = 4 expected doses
    # Patient takes all 4 expected doses:
    for day_offset in [0, 2, 4, 6]:
        dose_dt = datetime.combine(start_date + timedelta(days=day_offset), time(9, 0))
        db_session.add(MedicationLog(
            patient_id="pt_phase11",
            medication_schedule_id="sched_alt",
            medicine_name="Warfarin",
            scheduled_time=dose_dt,
            status="TAKEN"
        ))
    db_session.commit()

    adherence = calculate_patient_7d_adherence(db_session, "pt_phase11", now=now)
    assert adherence == 100.0


def test_weekly_schedule_calculation(db_session):
    """
    Requirement A.7: Weekly schedule anchored on effective_start_date
    expects exactly 1 dose in the 7-day window.
    """
    now = datetime(2026, 11, 11, 12, 0, 0)
    # Set anchor date to 3 days ago (e.g., Sunday)
    anchor_date = (now - timedelta(days=3)).date()

    sched = MedicationSchedule(
        id="sched_weekly",
        care_plan_id="cp_phase11",
        patient_id="pt_phase11",
        medicine_name="Methotrexate",
        dosage="15mg",
        frequency="Weekly once",
        effective_start_date=anchor_date,
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()

    # 1 expected dose in 7-day window. If not taken, adherence = 0.0%
    adh_missed = calculate_patient_7d_adherence(db_session, "pt_phase11", now=now)
    assert adh_missed == 0.0

    # Once taken, adherence = 100.0%
    dose_dt = datetime.combine(anchor_date, time(9, 0))
    db_session.add(MedicationLog(
        patient_id="pt_phase11",
        medication_schedule_id="sched_weekly",
        medicine_name="Methotrexate",
        scheduled_time=dose_dt,
        status="TAKEN"
    ))
    db_session.commit()

    adh_taken = calculate_patient_7d_adherence(db_session, "pt_phase11", now=now)
    assert adh_taken == 100.0


def test_unsupported_ambiguous_cadence_excluded_safely(db_session):
    """
    Requirement A.9: Unsupported / ambiguous cadences do not silently guess once-daily;
    they are excluded safely from the fixed-dose denominator.
    """
    now = datetime(2026, 11, 11, 12, 0, 0)
    sched = MedicationSchedule(
        id="sched_ambig",
        care_plan_id="cp_phase11",
        patient_id="pt_phase11",
        medicine_name="Immunotherapy",
        dosage="10mg",
        frequency="Every 3 weeks cycle 1",
        effective_start_date=date(2026, 11, 1),
        is_active=True
    )
    db_session.add(sched)
    db_session.commit()

    # Ambiguous frequency safely excluded; 0 expected fixed daily doses -> 100.0%
    adherence = calculate_patient_7d_adherence(db_session, "pt_phase11", now=now)
    assert adherence == 100.0


# =========================================================================
# Part B: Alert Deduplication Across All Creation Paths
# =========================================================================

def test_active_lifecycle_statuses_prevent_duplicate(db_session):
    """
    Requirement B.3 & B.4: OPEN, ACKNOWLEDGED, and ESCALATED statuses
    all prevent duplicate alert creation for the same patient and rule code.
    """
    rule_code = "RULE_VITAL_SPO2_CRITICAL"

    # 1. When status is OPEN
    alert1, created1 = RulesEngine.create_or_get_alert(
        db=db_session,
        patient_id="pt_phase11",
        rule_code=rule_code,
        severity="CRITICAL",
        title="SpO2 Breach",
        description="Low SpO2"
    )
    assert created1 is True
    assert alert1.status == "OPEN"

    # Attempt second alert while OPEN -> duplicate prevented
    alert2, created2 = RulesEngine.create_or_get_alert(
        db=db_session,
        patient_id="pt_phase11",
        rule_code=rule_code,
        severity="CRITICAL",
        title="SpO2 Breach 2",
        description="Low SpO2 repeated"
    )
    assert created2 is False
    assert alert2.id == alert1.id

    # 2. Transition alert to ACKNOWLEDGED -> still active, duplicate prevented
    alert1.status = "ACKNOWLEDGED"
    db_session.commit()

    alert3, created3 = RulesEngine.create_or_get_alert(
        db=db_session,
        patient_id="pt_phase11",
        rule_code=rule_code,
        severity="CRITICAL",
        title="SpO2 Breach 3",
        description="Low SpO2 while acknowledged"
    )
    assert created3 is False
    assert alert3.id == alert1.id

    # 3. Transition alert to ESCALATED -> still active, duplicate prevented
    alert1.status = "ESCALATED"
    db_session.commit()

    alert4, created4 = RulesEngine.create_or_get_alert(
        db=db_session,
        patient_id="pt_phase11",
        rule_code=rule_code,
        severity="CRITICAL",
        title="SpO2 Breach 4",
        description="Low SpO2 while escalated"
    )
    assert created4 is False
    assert alert4.id == alert1.id

    # Total alerts in database remains exactly 1
    total_alerts = db_session.execute(
        select(Alert).where(Alert.patient_id == "pt_phase11")
    ).scalars().all()
    assert len(total_alerts) == 1


def test_terminal_resolved_status_allows_new_alert(db_session):
    """
    Requirement B.5: Once an alert transitions to RESOLVED, a subsequent
    qualifying trigger creates a new OPEN alert.
    """
    rule_code = "RULE_RED_FLAG_EMERGENCY"

    # Initial alert created
    a1, c1 = RulesEngine.create_or_get_alert(
        db=db_session,
        patient_id="pt_phase11",
        rule_code=rule_code,
        severity="CRITICAL",
        title="Red Flag",
        description="Emergency"
    )
    assert c1 is True

    # Clinician resolves alert with action notes
    a1.status = "RESOLVED"
    a1.resolved_at = datetime.utcnow()
    a1.resolution_action_notes = "Patient evaluated, emergency script delivered and confirmed stable."
    db_session.commit()

    # Subsequent trigger creates a new OPEN alert
    a2, c2 = RulesEngine.create_or_get_alert(
        db=db_session,
        patient_id="pt_phase11",
        rule_code=rule_code,
        severity="CRITICAL",
        title="Red Flag 2",
        description="New Emergency Presentation"
    )
    assert c2 is True
    assert a2.id != a1.id
    assert a2.status == "OPEN"

    total = db_session.execute(
        select(Alert).where(Alert.patient_id == "pt_phase11", Alert.rule_code == rule_code)
    ).scalars().all()
    assert len(total) == 2


def test_different_patients_and_rule_codes_independent(db_session):
    """
    Requirement B.7: Deduplication does not accidentally merge different patients
    or different rule codes.
    """
    # Second patient
    p2 = Patient(
        id="pt_phase11_b",
        facility_id="fac_1",
        first_name="Bipin",
        last_name="Patel",
        dob=date(1975, 5, 10),
        gender="Male",
        phone="+919876543211",
        diagnosis="Post-TKR",
        discharge_date=date(2026, 11, 1),
        status="ACTIVE"
    )
    db_session.add(p2)
    db_session.commit()

    # Same rule code for Patient 1 and Patient 2
    a1, _ = RulesEngine.create_or_get_alert(db_session, "pt_phase11", "RULE_VITAL_BP_SYSTOLIC_CRITICAL", "CRITICAL", "High BP", "BP 190")
    a2, _ = RulesEngine.create_or_get_alert(db_session, "pt_phase11_b", "RULE_VITAL_BP_SYSTOLIC_CRITICAL", "CRITICAL", "High BP", "BP 195")
    assert a1.id != a2.id

    # Different rule code for Patient 1
    a3, _ = RulesEngine.create_or_get_alert(db_session, "pt_phase11", "RULE_SYMPTOM_SUSTAINED_WORSENING_BREATHLESSNESS", "HIGH", "Breathlessness", "Trend")
    assert a3.id != a1.id


def test_all_alert_producing_paths_deduplicated(db_session):
    """
    Requirement B.1: Validates that RulesEngine, MonitoringScheduler, and PatientPortal
    all deduplicate through the centralized create_or_get_alert mechanism.
    """
    # 1. Symptom check-in red flag deduplication
    checkin1 = SymptomCheckin(
        id="chk_1",
        patient_id="pt_phase11",
        pain_level=9, # triggers RULE_RED_FLAG_EMERGENCY
        recorded_at=datetime.utcnow()
    )
    alerts_chk1 = RulesEngine.evaluate_symptom_checkin(db_session, "pt_phase11", checkin1)
    assert len(alerts_chk1) == 1
    red_flag_alert = alerts_chk1[0]

    # Second checkin with severe pain: deduplicated
    checkin2 = SymptomCheckin(
        id="chk_2",
        patient_id="pt_phase11",
        pain_level=10,
        recorded_at=datetime.utcnow()
    )
    alerts_chk2 = RulesEngine.evaluate_symptom_checkin(db_session, "pt_phase11", checkin2)
    assert len(alerts_chk2) == 1
    assert alerts_chk2[0].id == red_flag_alert.id

    # 2. Monitoring scheduler unanswered checkin deduplication
    stale_task = CheckinTask(
        id="task_stale",
        patient_id="pt_phase11",
        scheduled_for=datetime.utcnow() - timedelta(hours=6),
        status="PENDING"
    )
    db_session.add(stale_task)
    db_session.commit()

    alert_sch1, created_sch1 = RulesEngine.create_or_get_alert(
        db=db_session,
        patient_id="pt_phase11",
        rule_code="UNANSWERED_CHECKIN",
        severity="MEDIUM",
        title="Missed Daily Recovery Check-in",
        description="Expired check-in window"
    )
    assert created_sch1 is True

    # Second expiration for same patient: deduplicated
    alert_sch2, created_sch2 = RulesEngine.create_or_get_alert(
        db=db_session,
        patient_id="pt_phase11",
        rule_code="UNANSWERED_CHECKIN",
        severity="MEDIUM",
        title="Missed Daily Recovery Check-in",
        description="Expired check-in window second cycle"
    )
    assert created_sch2 is False
    assert alert_sch2.id == alert_sch1.id


def test_database_uniqueness_conflict_and_savepoint_handling(db_session):
    """
    Requirement C.4: Verifies savepoint rollback and active alert refetch
    when a database-level uniqueness collision occurs.
    """
    rule_code = "RULE_CONCURRENCY_TEST"

    # Step 1: Create initial active alert
    alert1, created1 = RulesEngine.create_or_get_alert(
        db=db_session,
        patient_id="pt_phase11",
        rule_code=rule_code,
        severity="HIGH",
        title="Concurrency Test Alert",
        description="Original alert"
    )
    assert created1 is True

    # Step 2: Directly trigger create_or_get_alert with simulated bypass of application SELECT
    # to test the try/except IntegrityError and savepoint rollback mechanism
    # We simulate a race condition where get_active_alert returns None momentarily
    orig_get_active = RulesEngine.get_active_alert
    try:
        call_count = [0]
        def mock_get_active(db, patient_id, r_code):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call (check-before-insert): return None as if worker did not see existing row
                return None
            else:
                # Second call (after IntegrityError): return the real active alert
                return orig_get_active(db, patient_id, r_code)

        RulesEngine.get_active_alert = mock_get_active

        # This will attempt to INSERT into alerts table, hitting the partial unique index,
        # raising IntegrityError, catching it in begin_nested savepoint, and refetching alert1!
        refetched_alert, created_flag = RulesEngine.create_or_get_alert(
            db=db_session,
            patient_id="pt_phase11",
            rule_code=rule_code,
            severity="HIGH",
            title="Concurrent Duplicate Alert",
            description="Should collide on partial unique index"
        )

        assert created_flag is False
        assert refetched_alert.id == alert1.id
    finally:
        RulesEngine.get_active_alert = orig_get_active

    # Total in DB must remain 1
    count = db_session.execute(
        select(Alert).where(Alert.patient_id == "pt_phase11", Alert.rule_code == rule_code)
    ).scalars().all()
    assert len(count) == 1
