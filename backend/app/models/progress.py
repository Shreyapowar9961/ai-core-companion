import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Float, Boolean, Date, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class DailyProgressScore(Base):
    __tablename__ = "daily_progress_scores"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, index=True)
    score_date = Column(Date, default=date.today, index=True)
    
    # Weighted components (PR-01)
    medication_score = Column(Float, default=100.0)
    checkin_score = Column(Float, default=100.0)
    hydration_score = Column(Float, default=100.0)
    activity_score = Column(Float, default=100.0)
    overall_score = Column(Float, default=100.0)
    
    # Trend flags (PR-06)
    is_declining = Column(Boolean, default=False)
    declining_indicators = Column(JSON, default=list) # e.g. ["medication", "activity"]
    calculation_breakdown = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    patient = relationship("Patient", back_populates="progress_scores")

class PatientSummary(Base):
    __tablename__ = "patient_summaries"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, index=True)
    summary_date = Column(Date, default=date.today, index=True)
    
    # PATIENT_VOICE (PR-02), CAREGIVER_SIMPLIFIED (PR-03)
    summary_type = Column(String(32), default="PATIENT_VOICE")
    language = Column(String(16), default="en")
    content = Column(Text, nullable=False)
    
    delivered_via = Column(String(32), default="VOICE_CALL") # VOICE_CALL, SMS, WHATSAPP
    is_delivered = Column(Boolean, default=False)
    delivered_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    patient = relationship("Patient", back_populates="summaries")
