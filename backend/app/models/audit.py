import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text
from app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    # GV-03: calls, reminders, responses, confirmations, alerts, escalations, handoffs, consent, access
    event_type = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(128), nullable=False)
    actor_role = Column(String(32), default="SYSTEM")
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=True, index=True)
    
    resource = Column(String(64), nullable=False)
    details_json = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class ConfigAuditLog(Base):
    __tablename__ = "config_audit_logs"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    # GV-04: schedules, thresholds, questionnaires, rules, and content
    config_type = Column(String(64), nullable=False, index=True) # RULE, SCHEDULE, THRESHOLD, CONTENT
    item_id = Column(String(64), nullable=False, index=True)
    changed_by = Column(String(128), nullable=False)
    
    old_value_json = Column(JSON, nullable=True)
    new_value_json = Column(JSON, nullable=False)
    change_reason = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
