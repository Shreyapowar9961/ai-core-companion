import os
import pytest
from datetime import datetime, date, time, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.patient import Facility, Patient, CarePlan
from app.models.clinical import MedicationSchedule, MedicationLog, VitalsThreshold
from app.models.rules_alert import Alert, AlertActionLog
from app.services.rules_engine import RulesEngine
from app.api.v1.dashboard import calculate_patient_7d_adherence, parse_schedule_dose_times

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

    fac = session.query(Facility).filter(Facility.id == "facility-apex-1").first()
    if not fac:
        fac = Facility(id="facility-apex-1", name="Apex Memorial Hospital", location="Pune")
        session.add(fac)
        session.flush()

    try:
        yield session
    finally:
        try:
            test_pt_ids = ["pt-1", "pt-2", "pt-3", "pt-4", "pt-5", "pt-6", "pat-dedup-1", "pat-dedup-2", "pat-diff-1", "pat-res-1", "pat-sla-1"]
            session.query(AlertActionLog).filter(AlertActionLog.patient_id.in_(test_pt_ids)).delete(synchronize_session=False)
            session.query(Alert).filter(Alert.patient_id.in_(test_pt_ids)).delete(synchronize_session=False)
            session.query(MedicationLog).filter(MedicationLog.patient_id.in_(test_pt_ids)).delete(synchronize_session=False)
            session.query(MedicationSchedule).filter(MedicationSchedule.patient_id.in_(test_pt_ids)).delete(synchronize_session=False)
            session.query(CarePlan).filter(CarePlan.patient_id.in_(test_pt_ids)).delete(synchronize_session=False)
            session.query(Patient).filter(Patient.id.in_(test_pt_ids)).delete(synchronize_session=False)
            session.commit()
        except Exception:
            session.rollback()
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


# ==============================================================================
# STEP 2: DYNAMIC MEDICATION ADHERENCE TESTS (6 REQUIRED TEST CASES)
# ==============================================================================

def test_adherence_all_expected_doses_taken(db_session):
    """
    Test Case 1: All expected doses taken over the previous 7 days -> 100.0%.
    """
    ref_now = datetime(2026, 11, 10, 12, 0, 0)
    p = Patient(id="pt-1", first_name="Ramesh", last_name="Patil", dob=date(1955, 6, 12),
                gender="Male", phone="+919820011223", diagnosis="Post-CABG", discharge_date=date(2026, 11, 1))
    cp = CarePlan(id="cp-1", patient_id="pt-1", is_active=True)
    db_session.add_all([p, cp])
    db_session.commit()

    # Schedule: Once daily at 09:00 for the entire 7-day window (7 expected doses)
    sched = MedicationSchedule(
        id="sch-1", care_plan_id="cp-1", patient_id="pt-1",
        medicine_name="Telmisartan", dosage="40mg", frequency="Once daily",
        dose_times=["09:00"], effective_start_date=date(2026, 11, 1), is_active=True
    )
    db_session.add(sched)

    # 7 doses confirmed as TAKEN
    for i in range(7):
        log_dt = datetime(2026, 11, 4 + i, 9, 0, 0)
        log = MedicationLog(
            id=f"log-take-{i}", patient_id="pt-1", medication_schedule_id="sch-1",
            medicine_name="Telmisartan", dosage="40mg", scheduled_time=log_dt,
            actual_time=log_dt, status="TAKEN"
        )
        db_session.add(log)
    db_session.commit()

    adherence = calculate_patient_7d_adherence(db_session, "pt-1", now=ref_now)
    assert adherence == 100.0


def test_adherence_some_doses_missed(db_session):
    """
    Test Case 2: Some doses missed (5 taken, 2 missed out of 7 expected doses) -> 71.4%.
    """
    ref_now = datetime(2026, 11, 10, 12, 0, 0)
    p = Patient(id="pt-2", first_name="Sunita", last_name="Deshmukh", dob=date(1962, 4, 18),
                gender="Female", phone="+919820044556", diagnosis="Post-Angioplasty", discharge_date=date(2026, 11, 1))
    cp = CarePlan(id="cp-2", patient_id="pt-2", is_active=True)
    db_session.add_all([p, cp])

    sched = MedicationSchedule(
        id="sch-2", care_plan_id="cp-2", patient_id="pt-2",
        medicine_name="Atorvastatin", dosage="20mg", frequency="Once daily",
        dose_times=["09:00"], effective_start_date=date(2026, 11, 1), is_active=True
    )
    db_session.add(sched)

    # 5 doses TAKEN, 2 doses MISSED
    for i in range(7):
        log_dt = datetime(2026, 11, 4 + i, 9, 0, 0)
        status = "MISSED" if i in [2, 5] else "TAKEN"
        log = MedicationLog(
            id=f"log-p2-{i}", patient_id="pt-2", medication_schedule_id="sch-2",
            medicine_name="Atorvastatin", dosage="20mg", scheduled_time=log_dt,
            status=status, stated_reason="Forgot dose" if status == "MISSED" else None
        )
        db_session.add(log)
    db_session.commit()

    adherence = calculate_patient_7d_adherence(db_session, "pt-2", now=ref_now)
    # 5 / 7 * 100 = 71.428... -> 71.4
    assert adherence == 71.4


def test_adherence_no_expected_doses(db_session):
    """
    Test Case 3: No expected doses (no schedules or zero doses in window) -> handles division by zero safely.
    """
    ref_now = datetime(2026, 11, 10, 12, 0, 0)
    p = Patient(id="pt-3", first_name="Aarav", last_name="Mehta", dob=date(1985, 1, 10),
                gender="Male", phone="+919820099887", diagnosis="Observation", discharge_date=date(2026, 11, 1))
    db_session.add(p)
    db_session.commit()

    adherence = calculate_patient_7d_adherence(db_session, "pt-3", now=ref_now)
    assert adherence == 100.0


def test_adherence_multiple_medication_schedules(db_session):
    """
    Test Case 4: Multiple medication schedules with different frequencies:
    Schedule A (Once daily = 7 doses) + Schedule B (Twice daily = 14 doses) = 21 expected doses.
    Patient takes all 14 doses of Schedule B, misses all 7 of Schedule A -> 14/21 = 66.7%.
    """
    ref_now = datetime(2026, 11, 10, 12, 0, 0)
    p = Patient(id="pt-4", first_name="Kavita", last_name="Joshi", dob=date(1970, 8, 22),
                gender="Female", phone="+919820033112", diagnosis="Post-Valve Replacement", discharge_date=date(2026, 11, 1))
    cp = CarePlan(id="cp-4", patient_id="pt-4", is_active=True)
    db_session.add_all([p, cp])

    # Schedule A: Once daily at 09:00 (7 expected in 7d)
    sch_a = MedicationSchedule(
        id="sch-4a", care_plan_id="cp-4", patient_id="pt-4",
        medicine_name="Ecosprin", dosage="75mg", frequency="Once daily",
        dose_times=["09:00"], effective_start_date=date(2026, 11, 1), is_active=True
    )
    # Schedule B: Twice daily at 09:00 and 21:00 (14 expected in 7d)
    # Note: on ref_now day Nov 10, 21:00 is after 12:00, but Nov 3 21:00 is after Nov 3 12:00.
    # Total doses between Nov 3 12:00 and Nov 10 12:00:
    # Nov 3 21:00 (1) + Nov 4-9 (6 days * 2 = 12) + Nov 10 09:00 (1) = 14 doses.
    sch_b = MedicationSchedule(
        id="sch-4b", care_plan_id="cp-4", patient_id="pt-4",
        medicine_name="Metoprolol", dosage="25mg", frequency="Twice daily",
        dose_times=["09:00", "21:00"], effective_start_date=date(2026, 11, 1), is_active=True
    )
    db_session.add_all([sch_a, sch_b])

    # Patient takes all 14 doses of Metoprolol, takes 0 doses of Ecosprin
    log_id = 0
    # Nov 3 evening dose
    db_session.add(MedicationLog(
        id=f"log-4-{log_id}", patient_id="pt-4", medication_schedule_id="sch-4b",
        medicine_name="Metoprolol", dosage="25mg", scheduled_time=datetime(2026, 11, 3, 21, 0),
        status="TAKEN"
    ))
    log_id += 1
    # Nov 4 to Nov 9 (morning and evening)
    for day in range(4, 10):
        for h in [9, 21]:
            db_session.add(MedicationLog(
                id=f"log-4-{log_id}", patient_id="pt-4", medication_schedule_id="sch-4b",
                medicine_name="Metoprolol", dosage="25mg", scheduled_time=datetime(2026, 11, day, h, 0),
                status="TAKEN"
            ))
            log_id += 1
    # Nov 10 morning dose
    db_session.add(MedicationLog(
        id=f"log-4-{log_id}", patient_id="pt-4", medication_schedule_id="sch-4b",
        medicine_name="Metoprolol", dosage="25mg", scheduled_time=datetime(2026, 11, 10, 9, 0),
        status="TAKEN"
    ))
    db_session.commit()

    adherence = calculate_patient_7d_adherence(db_session, "pt-4", now=ref_now)
    # Expected: 7 (Ecosprin) + 14 (Metoprolol) = 21 expected.
    # Taken: 14. Adherence: 14 / 21 * 100 = 66.666... -> 66.7
    assert adherence == 66.7


def test_adherence_schedule_activated_partway_through_window(db_session):
    """
    Test Case 5: Schedule activated partway through the seven-day window.
    Window is Nov 3 12:00 to Nov 10 12:00 (7 days).
    Schedule activated on Nov 8 (effective_start_date = 2026-11-08).
    Days Nov 3 to Nov 7 have zero expected doses.
    Only Nov 8, 9, 10 at 09:00 are expected (3 doses).
    Patient takes all 3 doses -> 100.0%.
    """
    ref_now = datetime(2026, 11, 10, 12, 0, 0)
    p = Patient(id="pt-5", first_name="Vikram", last_name="Shinde", dob=date(1975, 11, 3),
                gender="Male", phone="+919820066778", diagnosis="PCI", discharge_date=date(2026, 11, 7))
    cp = CarePlan(id="cp-5", patient_id="pt-5", is_active=True)
    db_session.add_all([p, cp])

    sched = MedicationSchedule(
        id="sch-5", care_plan_id="cp-5", patient_id="pt-5",
        medicine_name="Rosuvastatin", dosage="10mg", frequency="Once daily",
        dose_times=["09:00"], effective_start_date=date(2026, 11, 8), is_active=True
    )
    db_session.add(sched)

    # 3 doses taken (Nov 8, Nov 9, Nov 10)
    for i, d in enumerate([8, 9, 10]):
        log = MedicationLog(
            id=f"log-5-{i}", patient_id="pt-5", medication_schedule_id="sch-5",
            medicine_name="Rosuvastatin", dosage="10mg", scheduled_time=datetime(2026, 11, d, 9, 0),
            status="TAKEN"
        )
        db_session.add(log)
    db_session.commit()

    adherence = calculate_patient_7d_adherence(db_session, "pt-5", now=ref_now)
    assert adherence == 100.0


def test_adherence_boundary_dates_and_times(db_session):
    """
    Test Case 6: Boundary dates and times:
    - Avoids counting future doses scheduled after `now` (e.g. today at 20:00 when now is 12:00).
    - Avoids counting doses prior to window start (e.g. 7 days ago at 08:00 when window starts at 12:00).
    - Avoids counting doses after effective_end_date.
    """
    ref_now = datetime(2026, 11, 10, 12, 0, 0)
    # Window start is exactly 2026-11-03 12:00:00
    p = Patient(id="pt-6", first_name="Ananya", last_name="Verma", dob=date(1990, 2, 14),
                gender="Female", phone="+919820077889", diagnosis="Post-Op", discharge_date=date(2026, 10, 25))
    cp = CarePlan(id="cp-6", patient_id="pt-6", is_active=True)
    db_session.add_all([p, cp])

    # Schedule: Twice daily at 09:00 and 18:00
    # effective_end_date = 2026-11-07 (ended 3 days ago)
    sched = MedicationSchedule(
        id="sch-6", care_plan_id="cp-6", patient_id="pt-6",
        medicine_name="Pantoprazole", dosage="40mg", frequency="Twice daily",
        dose_times=["09:00", "18:00"], effective_start_date=date(2026, 11, 1),
        effective_end_date=date(2026, 11, 7), is_active=True
    )
    db_session.add(sched)

    # In 7-day window (Nov 3 12:00 to Nov 10 12:00):
    # Nov 3: 09:00 is BEFORE window_start (12:00) -> NOT expected!
    # Nov 3: 18:00 is inside window -> EXPECTED (1)
    # Nov 4, 5, 6, 7: 4 days * 2 = 8 doses -> EXPECTED (8)
    # Nov 8, 9, 10: past effective_end_date -> NOT expected!
    # Total expected = 1 + 8 = 9 doses.

    # Suppose patient took 9 doses
    db_session.add(MedicationLog(
        id="log-b-1", patient_id="pt-6", medication_schedule_id="sch-6",
        medicine_name="Pantoprazole", dosage="40mg", scheduled_time=datetime(2026, 11, 3, 18, 0),
        status="TAKEN"
    ))
    for d in range(4, 8):
        for h in [9, 18]:
            db_session.add(MedicationLog(
                id=f"log-b-{d}-{h}", patient_id="pt-6", medication_schedule_id="sch-6",
                medicine_name="Pantoprazole", dosage="40mg", scheduled_time=datetime(2026, 11, d, h, 0),
                status="TAKEN"
            ))
    db_session.commit()

    adherence = calculate_patient_7d_adherence(db_session, "pt-6", now=ref_now)
    assert adherence == 100.0


# ==============================================================================
# STEP 3: ALERT DEDUPLICATION TESTS (5 REQUIRED TEST CASES)
# ==============================================================================

def test_deduplication_repeated_qualifying_readings(db_session):
    """
    Test Case 1: Repeated qualifying readings for the same patient and rule
    must return the existing OPEN alert without creating a duplicate in the database.
    """
    p = Patient(id="pat-dedup-1", first_name="Raj", last_name="Kapoor", dob=date(1950, 5, 1),
                gender="Male", phone="+919999900001", diagnosis="Heart Failure", discharge_date=date.today())
    db_session.add(p)
    db_session.commit()

    # Reading 1: SpO2 = 85.0% (Critical breach < 88%)
    status1, alert1 = RulesEngine.evaluate_vital_reading(
        db=db_session, patient_id="pat-dedup-1", vital_type="SPO2", value=85.0, unit="%"
    )
    assert status1 == "CRITICAL"
    assert alert1 is not None
    assert alert1.status == "OPEN"
    alert_id = alert1.id

    # Verify exactly 1 alert exists in the database
    alerts_in_db = db_session.query(Alert).filter(Alert.patient_id == "pat-dedup-1").all()
    assert len(alerts_in_db) == 1
    action_logs_in_db = db_session.query(AlertActionLog).filter(AlertActionLog.alert_id == alert_id).all()
    assert len(action_logs_in_db) == 1

    # Reading 2: SpO2 = 84.0% (Second critical breach for same patient and same rule)
    status2, alert2 = RulesEngine.evaluate_vital_reading(
        db=db_session, patient_id="pat-dedup-1", vital_type="SPO2", value=84.0, unit="%"
    )
    assert status2 == "CRITICAL"
    assert alert2 is not None
    # Must return the existing open alert without creating a duplicate
    assert alert2.id == alert_id

    # Verify database still contains strictly 1 alert
    alerts_after = db_session.query(Alert).filter(Alert.patient_id == "pat-dedup-1").all()
    assert len(alerts_after) == 1
    # Verify no duplicate action logs created
    action_logs_after = db_session.query(AlertActionLog).filter(AlertActionLog.alert_id == alert_id).all()
    assert len(action_logs_after) == 1


def test_deduplication_same_rule_different_patients(db_session):
    """
    Test Case 2: Same rule triggered for different patients must NOT be suppressed;
    each patient must receive their own distinct alert.
    """
    p1 = Patient(id="pat-diff-1", first_name="Amit", last_name="Roy", dob=date(1965, 3, 10),
                 gender="Male", phone="+919999900011", diagnosis="CAD", discharge_date=date.today())
    p2 = Patient(id="pat-diff-2", first_name="Deepa", last_name="Nair", dob=date(1972, 7, 19),
                 gender="Female", phone="+919999900012", diagnosis="CAD", discharge_date=date.today())
    db_session.add_all([p1, p2])
    db_session.commit()

    # Patient 1 critical reading
    status1, alert1 = RulesEngine.evaluate_vital_reading(
        db=db_session, patient_id="pat-diff-1", vital_type="SPO2", value=85.0, unit="%"
    )
    assert status1 == "CRITICAL"
    assert alert1.patient_id == "pat-diff-1"

    # Patient 2 critical reading for the SAME rule code
    status2, alert2 = RulesEngine.evaluate_vital_reading(
        db=db_session, patient_id="pat-diff-2", vital_type="SPO2", value=86.0, unit="%"
    )
    assert status2 == "CRITICAL"
    assert alert2.patient_id == "pat-diff-2"
    assert alert2.id != alert1.id

    # Total alerts for the two patients must be 2
    total_alerts = db_session.query(Alert).filter(Alert.patient_id.in_(["pat-diff-1", "pat-diff-2"])).all()
    assert len(total_alerts) == 2


def test_deduplication_different_rules_same_patient(db_session):
    """
    Test Case 3: Different rules for the same patient must NOT be suppressed;
    e.g., critical SpO2 alert and critical Systolic BP alert must both exist.
    """
    p = Patient(id="pat-diff-rules", first_name="Manoj", last_name="Tiwari", dob=date(1958, 9, 2),
                gender="Male", phone="+919999900021", diagnosis="Post-CABG", discharge_date=date.today())
    db_session.add(p)
    db_session.commit()

    # Rule 1: SpO2 critical desaturation (<88%)
    s1, a1 = RulesEngine.evaluate_vital_reading(
        db=db_session, patient_id="pat-diff-rules", vital_type="SPO2", value=85.0, unit="%"
    )
    assert s1 == "CRITICAL"
    assert a1.rule_code == "RULE_VITAL_SPO2_CRITICAL"

    # Rule 2: Hypertensive crisis (Systolic BP > 180)
    s2, a2 = RulesEngine.evaluate_vital_reading(
        db=db_session, patient_id="pat-diff-rules", vital_type="BP_SYSTOLIC", value=195.0, unit="mmHg"
    )
    assert s2 == "CRITICAL"
    assert a2.rule_code == "RULE_VITAL_BP_SYSTOLIC_CRITICAL"
    assert a2.id != a1.id

    patient_alerts = db_session.query(Alert).filter(Alert.patient_id == "pat-diff-rules").all()
    assert len(patient_alerts) == 2


def test_deduplication_new_alert_after_resolved(db_session):
    """
    Test Case 4: Once an existing alert is resolved/closed, a later qualifying reading
    MUST create a new alert.
    """
    p = Patient(id="pat-res-1", first_name="Sneha", last_name="Bhide", dob=date(1964, 12, 11),
                gender="Female", phone="+919999900031", diagnosis="Arrhythmia", discharge_date=date.today())
    db_session.add(p)
    db_session.commit()

    # Reading 1 -> Alert 1 (OPEN)
    s1, a1 = RulesEngine.evaluate_vital_reading(
        db=db_session, patient_id="pat-res-1", vital_type="SPO2", value=85.0, unit="%"
    )
    assert a1.status == "OPEN"
    a1_id = a1.id

    # Clinician reviews and resolves Alert 1
    a1.status = "RESOLVED"
    a1.resolved_at = datetime.utcnow()
    a1.resolved_by = "Dr. Neha Kulkarni"
    a1.resolution_action_notes = "Supplemental oxygen administered in clinic; patient stable."
    db_session.commit()

    # Reading 2 later in the day: SpO2 drops again to 86.0%
    s2, a2 = RulesEngine.evaluate_vital_reading(
        db=db_session, patient_id="pat-res-1", vital_type="SPO2", value=86.0, unit="%"
    )
    assert s2 == "CRITICAL"
    assert a2 is not None
    assert a2.status == "OPEN"
    # Must be a newly generated alert, not the resolved one
    assert a2.id != a1_id

    # Total alerts for patient must now be 2: one RESOLVED, one OPEN
    all_alerts = db_session.query(Alert).filter(Alert.patient_id == "pat-res-1").all()
    assert len(all_alerts) == 2
    statuses = {a.status for a in all_alerts}
    assert statuses == {"RESOLVED", "OPEN"}


def test_deduplication_preserves_severity_and_sla(db_session):
    """
    Test Case 5: When an alert is deduplicated, the existing alert's severity,
    SLA due date, created_at, and metadata remain untouched.
    """
    p = Patient(id="pat-sla-1", first_name="Girish", last_name="Pawar", dob=date(1959, 10, 5),
                gender="Male", phone="+919999900041", diagnosis="Hypertension", discharge_date=date.today())
    db_session.add(p)
    db_session.commit()

    # Initial Warning breach: Systolic BP = 155 mmHg (Warning threshold > 150)
    s1, a1 = RulesEngine.evaluate_vital_reading(
        db=db_session, patient_id="pat-sla-1", vital_type="BP_SYSTOLIC", value=155.0, unit="mmHg"
    )
    assert s1 == "WARNING"
    assert a1.severity == "HIGH"
    orig_sla = a1.sla_due_at
    orig_created = a1.created_at
    orig_id = a1.id

    # Second warning reading: Systolic BP = 158 mmHg
    s2, a2 = RulesEngine.evaluate_vital_reading(
        db=db_session, patient_id="pat-sla-1", vital_type="BP_SYSTOLIC", value=158.0, unit="mmHg"
    )
    assert a2.id == orig_id
    assert a2.severity == "HIGH"
    assert a2.sla_due_at == orig_sla
    assert a2.created_at == orig_created
