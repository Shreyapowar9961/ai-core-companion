import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Float, Boolean, Date, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship as orm_relationship
from app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class Facility(Base):
    __tablename__ = "facilities"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    contact_phone = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    patients = orm_relationship("Patient", back_populates="facility")

class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    facility_id = Column(String(64), ForeignKey("facilities.id"), nullable=True)
    
    # Demographics (ON-01)
    first_name = Column(String(128), nullable=False)
    last_name = Column(String(128), nullable=False)
    dob = Column(Date, nullable=False)
    gender = Column(String(32), nullable=False)
    phone = Column(String(32), nullable=False, index=True)
    email = Column(String(128), nullable=True)
    address = Column(String(512), nullable=True)
    emergency_contact_phone = Column(String(32), nullable=True)
    
    # Discharge & Programme info (ON-01)
    diagnosis = Column(String(512), nullable=False)
    discharge_date = Column(Date, nullable=False)
    programme_duration_days = Column(Integer, default=30)
    preferred_language = Column(String(16), default="en") # 'mr', 'hi', 'en' (LN-01, LN-02)
    
    # Status & Lifecycle (ON-06, PL-01, PL-02, PL-03)
    status = Column(String(32), default="DRAFT", index=True)
    paused_at = Column(DateTime, nullable=True)
    pause_reason = Column(String(255), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Operating preferences (ON-05, CM-06)
    call_window_start = Column(String(8), default="09:00")
    call_window_end = Column(String(8), default="19:00")
    checkin_morning_time = Column(String(8), default="09:30")
    checkin_evening_time = Column(String(8), default="18:30")
    dnd_start = Column(String(8), default="21:00")
    dnd_end = Column(String(8), default="08:00")
    retry_limit = Column(Integer, default=3)
    max_deferrals = Column(Integer, default=2)
    
    # Clinical Contacts (ON-03)
    treating_doctor_name = Column(String(128), nullable=True)
    treating_doctor_phone = Column(String(64), nullable=True)
    treating_doctor_specialty = Column(String(128), nullable=True)
    escalation_contacts = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    facility = orm_relationship("Facility", back_populates="patients")
    caregivers = orm_relationship("Caregiver", back_populates="patient", cascade="all, delete-orphan")
    consent = orm_relationship("Consent", back_populates="patient", uselist=False, cascade="all, delete-orphan")
    care_plans = orm_relationship("CarePlan", back_populates="patient", cascade="all, delete-orphan")
    vitals = orm_relationship("VitalReading", back_populates="patient", cascade="all, delete-orphan")
    checkins = orm_relationship("SymptomCheckin", back_populates="patient", cascade="all, delete-orphan")
    medication_logs = orm_relationship("MedicationLog", back_populates="patient", cascade="all, delete-orphan")
    appointments = orm_relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    alerts = orm_relationship("Alert", back_populates="patient", cascade="all, delete-orphan")
    call_sessions = orm_relationship("CallSession", back_populates="patient", cascade="all, delete-orphan")
    progress_scores = orm_relationship("DailyProgressScore", back_populates="patient", cascade="all, delete-orphan")
    summaries = orm_relationship("PatientSummary", back_populates="patient", cascade="all, delete-orphan")

class Caregiver(Base):
    __tablename__ = "caregivers"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False)
    name = Column(String(128), nullable=False)
    relationship = Column(String(64), nullable=False) # e.g. "Spouse", "Daughter", "Son"
    phone = Column(String(32), nullable=False)
    email = Column(String(128), nullable=True)
    
    # Consented information categories & channels (ON-03, GV-02, ES-04, PR-03)
    is_authorized = Column(Boolean, default=True)
    consented_channels = Column(JSON, default=lambda: ["SMS", "WHATSAPP", "VOICE"])
    consented_categories = Column(JSON, default=lambda: ["medication", "vitals", "alerts", "appointments"])
    
    created_at = Column(DateTime, default=datetime.utcnow)
    patient = orm_relationship("Patient", back_populates="caregivers")

class Consent(Base):
    __tablename__ = "consents"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, unique=True)
    
    voice_contact = Column(Boolean, default=False)
    call_recording = Column(Boolean, default=False)
    data_processing = Column(Boolean, default=False)
    caregiver_disclosure = Column(Boolean, default=False)
    emergency_escalation = Column(Boolean, default=False)
    
    consented_at = Column(DateTime, nullable=True)
    withdrawn_at = Column(DateTime, nullable=True)
    withdrawal_scope = Column(String(32), nullable=True)
    consent_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    patient = orm_relationship("Patient", back_populates="consent")

class CarePlan(Base):
    __tablename__ = "care_plans"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    diet_instructions = Column(Text, nullable=True)
    hydration_target_glasses = Column(Integer, default=8)
    hydration_interval_hours = Column(Integer, default=2)
    activity_target_minutes = Column(Integer, default=20)
    activity_target_steps = Column(Integer, default=2000)
    physiotherapy_instructions = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    patient = orm_relationship("Patient", back_populates="care_plans")
    medications = orm_relationship("MedicationSchedule", back_populates="care_plan", cascade="all, delete-orphan")
    vitals_thresholds = orm_relationship("VitalsThreshold", back_populates="care_plan", cascade="all, delete-orphan")
