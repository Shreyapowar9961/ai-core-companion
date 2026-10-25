import pytest
from datetime import datetime, timedelta, date
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from app.models.patient import Patient
from app.models.clinical import SymptomCheckin, MedicationLog, VitalsThreshold
from app.models.rules_alert import Alert
from app.services.rules_engine import RulesEngine

class MockPostgresSession:
    """
    Mock SQLAlchemy Session mimicking PostgreSQL backend queries
    for deterministic clinical rules testing. Zero SQLite.
    """
    def __init__(self):
        self.added_objects = []
        self._custom_return = None

    def execute(self, stmt):
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = self._custom_return
        mock_scalars.all.return_value = self._custom_return if isinstance(self._custom_return, list) else []
        mock_result.scalars.return_value = mock_scalars
        return mock_result

    def add(self, obj):
        self.added_objects.append(obj)

    def add_all(self, objs):
        self.added_objects.extend(objs)

    def flush(self):
        pass

    def commit(self):
        pass

    def refresh(self, obj):
        pass

    def get(self, model, ident):
        return None

def test_deterministic_vitals_critical_threshold():
    """
    Mandate: All escalation logic runs in a deterministic rules engine - NEVER in the LLM.
    VT-03, VT-04, ES-01: Critical SpO2 < 88% must trigger Critical alert with 15-min SLA.
    """
    db = MockPostgresSession()
    # Mock no custom threshold so standard clinical threshold applies (<88% critical)
    db._custom_return = None

    status, alert = RulesEngine.evaluate_vital_reading(
        db=db,
        patient_id="patient-pg-1",
        vital_type="SPO2",
        value=86.0,
        unit="%"
    )

    assert status == "CRITICAL"
    assert alert is not None
    assert alert.severity == "CRITICAL"
    assert alert.rule_code == "RULE_VITAL_SPO2_CRITICAL"
    assert "86.0 %" in alert.title
    # Check SLA is 15 minutes
    sla_diff = (alert.sla_due_at - datetime.utcnow()).total_seconds()
    assert 800 <= sla_diff <= 950

def test_vitals_plausibility_check():
    """
    VT-02: Validate values against plausible ranges and reject implausible readings.
    """
    db = MockPostgresSession()
    status, alert = RulesEngine.evaluate_vital_reading(
        db=db,
        patient_id="patient-pg-1",
        vital_type="SPO2",
        value=150.0, # Implausible SpO2
        unit="%"
    )
    assert status == "IMPLAUSIBLE"
    assert alert is None

def test_red_flag_acute_symptom_emergency():
    """
    ES-03: On red-flag presentation (severe acute pain >= 8), deliver emergency script
    and raise critical alert.
    """
    db = MockPostgresSession()
    checkin = SymptomCheckin(
        patient_id="patient-pg-1",
        pain_level=9,
        breathlessness="none",
        comparison_with_yesterday={"pain": "worsened"}
    )

    alerts = RulesEngine.evaluate_symptom_checkin(db, "patient-pg-1", checkin)
    assert len(alerts) >= 1
    assert any(a.severity == "CRITICAL" and a.rule_code == "RULE_RED_FLAG_EMERGENCY" for a in alerts)

def test_sustained_worsening_trend():
    """
    CI-05: Detect sustained worsening trend across consecutive checkins and invoke escalation rule.
    """
    db = MockPostgresSession()
    # Mock previous checkins returning 2 consecutive days with worsened breathlessness
    prev1 = SymptomCheckin(
        patient_id="patient-pg-1",
        recorded_at=datetime.utcnow() - timedelta(days=1),
        breathlessness="moderate",
        comparison_with_yesterday={"breathlessness": "worsened"}
    )
    prev2 = SymptomCheckin(
        patient_id="patient-pg-1",
        recorded_at=datetime.utcnow() - timedelta(days=2),
        breathlessness="moderate",
        comparison_with_yesterday={"breathlessness": "worsened"}
    )
    db._custom_return = [prev1, prev2]

    current = SymptomCheckin(
        patient_id="patient-pg-1",
        recorded_at=datetime.utcnow(),
        breathlessness="moderate",
        comparison_with_yesterday={"breathlessness": "worsened"}
    )

    alerts = RulesEngine.evaluate_symptom_checkin(db, "patient-pg-1", current)
    assert any(a.rule_code == "RULE_SYMPTOM_SUSTAINED_WORSENING_BREATHLESSNESS" for a in alerts)

def test_medication_repeated_miss_escalation():
    """
    MD-05: Detect repeated misses against threshold (>=2 doses) and trigger escalation.
    """
    db = MockPostgresSession()
    # Mock 2 consecutive missed logs
    m1 = MedicationLog(
        patient_id="patient-pg-1",
        medicine_name="Amlodipine",
        scheduled_time=datetime.utcnow() - timedelta(days=1),
        status="MISSED",
        stated_reason="Forgot"
    )
    m2 = MedicationLog(
        patient_id="patient-pg-1",
        medicine_name="Amlodipine",
        scheduled_time=datetime.utcnow(),
        status="MISSED",
        stated_reason="Side effects"
    )
    db._custom_return = [m1, m2]

    alert = RulesEngine.evaluate_medication_miss(db, "patient-pg-1", "Amlodipine")
    assert alert is not None
    assert alert.rule_code == "RULE_MED_REPEATED_MISS"
    assert alert.severity == "HIGH"

def test_contact_failure_escalation():
    """
    CM-02: Escalate to caregiver and care team once configured contact attempts are exhausted.
    """
    db = MockPostgresSession()
    alert = RulesEngine.evaluate_contact_failure(
        db=db,
        patient_id="patient-pg-1",
        retry_count=3,
        retry_limit=3,
        last_disposition="NO_ANSWER"
    )
    assert alert is not None
    assert alert.rule_code == "RULE_CONTACT_FAILURE_EXHAUSTED"
    assert alert.severity == "HIGH"
