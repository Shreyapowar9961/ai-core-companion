import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class PushDeviceRegistration(Base):
    """
    PostgreSQL storage for FCM device tokens and push notification preferences.
    Enforces patient ownership, token lifecycle management, and privacy safeguards.
    """
    __tablename__ = "push_device_registrations"

    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, index=True)
    fcm_token = Column(Text, nullable=False, index=True)
    device_type = Column(String(32), default="web")  # web, android, ios
    user_agent = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    push_enabled = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_sent_at = Column(DateTime, nullable=True)
    invalidated_at = Column(DateTime, nullable=True)
    invalidation_reason = Column(String(64), nullable=True)

    patient = relationship("Patient", backref="push_device_registrations")
