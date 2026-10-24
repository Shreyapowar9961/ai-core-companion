import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Float, Boolean, Date, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class MedicationSchedule(Base):
    __tablename__ = "medication_schedules"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    care_plan_id = Column(String(64), ForeignKey("care_plans.id"), nullable=False)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, index=True)
    
    medicine_name = Column(String(255), nullable=False)
    dosage = Column(String(128), nullable=False) # e.g. "50mg", "1 tablet"
    frequency = Column(String(64), default="Once daily") # e.g. "Once daily", "Twice daily"
    dose_times = Column(JSON, default=list) # e.g. ["09:00", "20:00"]
    instructions = Column(String(255), nullable=True) # e.g. "Take after breakfast with water"
    route = Column(String(64), default="Oral") # Oral, Topical, Injection
    
    effective_start_date = Column(Date, default=date.today)
    effective_end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    care_plan = relationship("CarePlan", back_populates="medications")
    logs = relationship("MedicationLog", back_populates="schedule", cascade="all, delete-orphan")

class MedicationLog(Base):
    __tablename__ = "medication_logs"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, index=True)
    medication_schedule_id = Column(String(64), ForeignKey("medication_schedules.id"), nullable=True)
    medicine_name = Column(String(255), nullable=False)
    dosage = Column(String(128), nullable=True)
    
    scheduled_time = Column(DateTime, nullable=False, index=True)
    actual_time = Column(DateTime, nullable=True)
    # TAKEN, MISSED, PENDING, DEFERRED (MD-02, MD-03, MD-04)
    status = Column(String(32), default="PENDING", index=True)
    stated_reason = Column(String(255), nullable=True) # e.g. "Side effect: dizziness", "Forgot"
    deferral_count = Column(Integer, default=0) # Capped at patient.max_deferrals (MD-04)
    recorded_via = Column(String(32), default="VOICE_CALL") # VOICE_CALL, MANUAL_WEB, SMS
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    patient = relationship("Patient", back_populates="medication_logs")
    schedule = relationship("MedicationSchedule", back_populates="logs")

class VitalsThreshold(Base):
    __tablename__ = "vitals_thresholds"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    care_plan_id = Column(String(64), ForeignKey("care_plans.id"), nullable=False)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, index=True)
    
    # BP_SYSTOLIC, BP_DIASTOLIC, BLOOD_GLUCOSE, SPO2, TEMPERATURE, PULSE, WEIGHT (VT-01)
    vital_type = Column(String(64), nullable=False)
    unit = Column(String(32), nullable=False)
    
    # Plausible biological boundaries (VT-02)
    plausible_min = Column(Float, nullable=False)
    plausible_max = Column(Float, nullable=False)
    
    # Clinician-defined individual thresholds (VT-03)
    normal_min = Column(Float, nullable=True)
    normal_max = Column(Float, nullable=True)
    warning_min = Column(Float, nullable=True)
    warning_max = Column(Float, nullable=True)
    critical_min = Column(Float, nullable=True)
    critical_max = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    care_plan = relationship("CarePlan", back_populates="vitals_thresholds")

class VitalReading(Base):
    __tablename__ = "vital_readings"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, index=True)
    call_session_id = Column(String(64), ForeignKey("call_sessions.id"), nullable=True)
    
    vital_type = Column(String(64), nullable=False)
    value = Column(Float, nullable=True) # Null when NOT_PROVIDED (VT-05)
    secondary_value = Column(Float, nullable=True) # e.g. Diastolic for BP
    unit = Column(String(32), nullable=False)
    
    # NORMAL, WARNING, CRITICAL, NOT_PROVIDED, IMPLAUSIBLE (VT-02, VT-04, VT-05)
    status = Column(String(32), default="NORMAL", index=True)
    voice_confirmed = Column(Boolean, default=True) # Read back to patient for confirmation (VT-01)
    notes = Column(String(255), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    patient = relationship("Patient", back_populates="vitals")

class SymptomCheckin(Base):
    __tablename__ = "symptom_checkins"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, index=True)
    call_session_id = Column(String(64), ForeignKey("call_sessions.id"), nullable=True)
    
    checkin_type = Column(String(32), default="MORNING") # MORNING, EVENING (CI-01, CI-07)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Standard 9-item symptom set (CI-02)
    # Severity values: none, mild, moderate, severe
    pain_level = Column(Integer, default=0) # 0-10 scale
    weakness = Column(String(32), default="none")
    dizziness = Column(String(32), default="none")
    breathlessness = Column(String(32), default="none")
    swelling = Column(String(32), default="none")
    fever = Column(String(32), default="none")
    wound_status = Column(String(64), default="healing_well") # healing_well, redness, discharge, pain
    appetite = Column(String(32), default="normal") # normal, reduced, none
    sleep_quality = Column(String(32), default="good") # good, fair, poor
    
    # Newly reported outside symptoms (CI-04)
    other_symptoms_verbatim = Column(Text, nullable=True)
    other_symptoms_structured = Column(JSON, default=dict)
    
    # Trend comparison with yesterday (CI-03, CI-06)
    # e.g. {"pain": "improved", "breathlessness": "worsened", "dizziness": "unchanged"}
    comparison_with_yesterday = Column(JSON, default=dict)
    
    patient = relationship("Patient", back_populates="checkins")

class LifestyleLog(Base):
    __tablename__ = "lifestyle_logs"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, index=True)
    
    # HYDRATION, ACTIVITY, PHYSIOTHERAPY, MEAL (LS-01, LS-02, LS-04, LS-05)
    log_type = Column(String(32), nullable=False)
    target_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    unit = Column(String(32), nullable=True) # e.g. "glasses", "minutes", "steps", "completion"
    
    # COMPLETED, PARTIAL, MISSED
    completion_status = Column(String(32), default="COMPLETED")
    reported_pain_difficulty = Column(Text, nullable=True) # e.g. pain during knee flex
    notes = Column(String(255), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
