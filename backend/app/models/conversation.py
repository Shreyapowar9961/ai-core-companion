import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class CallSession(Base):
    __tablename__ = "call_sessions"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, index=True)
    
    direction = Column(String(32), default="OUTBOUND") # OUTBOUND, INBOUND (CV-01)
    call_type = Column(String(64), default="MORNING_CHECKIN") # MORNING_CHECKIN, EVENING_CHECKIN, MEDICATION_REMINDER, APPOINTMENT_REMINDER
    
    # Status lifecycle
    status = Column(String(32), default="INITIATED", index=True) # INITIATED, RINGING, IN_PROGRESS, COMPLETED, INTERRUPTED, FAILED
    # Dispositions per CM-07
    disposition = Column(String(32), nullable=True, index=True) # COMPLETED, PARTIAL, NO_ANSWER, BUSY, UNREACHABLE, WRONG_PERSON, DECLINED, DISCONNECTED
    
    language_used = Column(String(16), default="en") # mr, hi, en (LN-01, LN-03)
    
    # Interruption recovery (CM-05)
    current_step_key = Column(String(64), default="WELCOME")
    interrupted_at = Column(DateTime, nullable=True)
    resume_context = Column(JSON, default=dict) # Persisted responses captured before disconnect
    
    # Deferral / DND handling (CM-03, CM-04)
    is_deferred = Column(Boolean, default=False)
    deferred_until = Column(DateTime, nullable=True)
    deferral_reason = Column(String(255), nullable=True)
    
    retry_count = Column(Integer, default=0) # (CM-01)
    duration_seconds = Column(Integer, default=0)
    caller_phone = Column(String(32), nullable=True)
    audio_url = Column(String(512), nullable=True) # (CV-08)
    
    # Handoff / Transfer details (CV-07)
    transferred_to_human = Column(Boolean, default=False)
    transfer_reason = Column(String(255), nullable=True)
    callback_requested = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    patient = relationship("Patient", back_populates="call_sessions")
    turns = relationship("CallTurn", back_populates="session", cascade="all, delete-orphan", order_by="CallTurn.turn_index")

class CallTurn(Base):
    __tablename__ = "call_turns"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    call_session_id = Column(String(64), ForeignKey("call_sessions.id"), nullable=False, index=True)
    
    turn_index = Column(Integer, nullable=False)
    step_key = Column(String(64), nullable=False) # e.g. "WELLBEING", "SYMPTOMS_PAIN", "VITALS_BP", "MEDICATION"
    agent_prompt = Column(Text, nullable=False)
    patient_audio_transcript = Column(Text, nullable=True) # (CV-08)
    detected_language = Column(String(16), nullable=True) # (LN-03, LN-04)
    
    intent = Column(String(64), nullable=True)
    extracted_entities = Column(JSON, default=dict) # Normalized data extracted
    
    # Repeat / Unanswered handling (CV-04, CV-05)
    repeated_count = Column(Integer, default=0)
    was_unanswered = Column(Boolean, default=False) # True if user gave no valid response
    
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("CallSession", back_populates="turns")
