import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, index=True)
    
    # AP-01: Remind about doctor, lab, therapy and follow-up
    appointment_type = Column(String(64), default="DOCTOR_FOLLOWUP") # DOCTOR_FOLLOWUP, LAB_TEST, PHYSIOTHERAPY
    scheduled_time = Column(DateTime, nullable=False, index=True)
    doctor_facility_name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    preparation_instructions = Column(Text, nullable=True) # e.g. "Overnight fasting required"
    
    # AP-02, AP-03, AP-05: Confirmation, reschedule, missed tracking
    status = Column(String(32), default="SCHEDULED", index=True) # SCHEDULED, CONFIRMED, DECLINED, UNCERTAIN, RESCHEDULE_REQUESTED, COMPLETED, MISSED
    attendance_confirmed_at = Column(DateTime, nullable=True)
    decline_reason = Column(String(255), nullable=True)
    
    # Rescheduling
    reschedule_reason = Column(String(255), nullable=True)
    reschedule_task_created = Column(Boolean, default=False)
    reschedule_notes = Column(Text, nullable=True)
    
    # AP-05: Non-attendance and repeated missed appointments
    missed_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    patient = relationship("Patient", back_populates="appointments")
