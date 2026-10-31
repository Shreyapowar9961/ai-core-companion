import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(String(64), primary_key=True, default=gen_uuid)
    email = Column(String(128), unique=True, nullable=False, index=True)
    full_name = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False, default="CLINICIAN") # CLINICIAN, ADMIN, PATIENT
    facility_id = Column(String(64), ForeignKey("facilities.id"), nullable=True, index=True)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    facility = relationship("Facility", backref="staff_profiles")

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    token_sig = Column(String(128), primary_key=True)
    user_id = Column(String(64), nullable=True)
    revoked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
