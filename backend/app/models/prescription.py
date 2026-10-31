import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class PrescriptionUpload(Base):
    """
    Prescription upload, free local OCR extraction, and clinician verification.
    """
    __tablename__ = "prescription_uploads"

    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, index=True)
    clinician_id = Column(String(64), nullable=True)

    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(64), nullable=False)

    # UPLOADED, OCR_PROCESSED, VERIFIED, REJECTED
    status = Column(String(32), default="UPLOADED", index=True)

    # Unverified OCR text output
    raw_ocr_text = Column(Text, nullable=True)
    # Draft extracted medications: [{name, dosage, frequency, times, duration, instructions}]
    extracted_medications = Column(JSON, default=list)
    # Final clinician-verified medications
    verified_medications = Column(JSON, default=list)

    clinician_notes = Column(Text, nullable=True)
    verified_by = Column(String(128), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    patient = relationship("Patient", backref="prescriptions")
