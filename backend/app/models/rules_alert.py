import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class EscalationRule(Base):
    __tablename__ = "escalation_rules"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    code = Column(String(64), unique=True, index=True) # e.g. "RULE_SPO2_CRITICAL"
    name = Column(String(255), nullable=False)
    # VITALS, SYMPTOMS, TREND, MEDICATION, CONTACT_FAILURE, COMPOSITE_DECLINE (ES-01, ES-08)
    category = Column(String(64), nullable=False, index=True)
    # CRITICAL, HIGH, MEDIUM, INFO (ES-06)
    severity = Column(String(32), nullable=False, index=True)
    
    # Clinician-configured condition definition (ES-01, ES-02)
    # e.g.:
    # {"type": "vital_threshold", "vital": "SPO2", "operator": "<", "value": 90}
    # {"type": "symptom_trend", "symptom": "breathlessness", "trend": "worsened", "consecutive_days": 2}
    # {"type": "medication_adherence", "consecutive_misses": 2}
    condition_json = Column(JSON, nullable=False)
    
    # Action payload configuration (ES-03, ES-04, ES-06)
    # e.g.: {"sla_minutes": 15, "emergency_script": true, "notify_caregiver": true, "notify_care_team": true}
    action_json = Column(JSON, nullable=False)
    
    is_active = Column(Boolean, default=True)
    facility_id = Column(String(64), ForeignKey("facilities.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    patient_id = Column(String(64), ForeignKey("patients.id"), nullable=False, index=True)
    rule_id = Column(String(64), ForeignKey("escalation_rules.id"), nullable=True)
    rule_code = Column(String(64), nullable=False, index=True)
    
    # CRITICAL, HIGH, MEDIUM, INFO (ES-06)
    severity = Column(String(32), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # ES-05: Supporting responses, trend, recent adherence history
    supporting_data = Column(JSON, default=dict)
    
    # OPEN, ACKNOWLEDGED, ESCALATED, RESOLVED (ES-06, ES-07, DB-04)
    status = Column(String(32), default="OPEN", index=True)
    sla_due_at = Column(DateTime, nullable=False, index=True)
    
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(128), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(128), nullable=True)
    resolution_action_notes = Column(Text, nullable=True) # DB-04, ES-07: Explicit closure by named user
    
    # Caregiver notification & SLA (ES-04)
    caregiver_notified = Column(Boolean, default=False)
    caregiver_ack_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    patient = relationship("Patient", back_populates="alerts")
    action_logs = relationship("AlertActionLog", back_populates="alert", cascade="all, delete-orphan", order_by="AlertActionLog.created_at")

class AlertActionLog(Base):
    __tablename__ = "alert_action_logs"
    
    id = Column(String(64), primary_key=True, default=gen_uuid)
    alert_id = Column(String(64), ForeignKey("alerts.id"), nullable=False, index=True)
    user_id = Column(String(128), nullable=False)
    user_name = Column(String(128), nullable=False)
    
    # CREATED, ACKNOWLEDGED, ESCALATED, RESOLVED
    action = Column(String(32), nullable=False)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    alert = relationship("Alert", back_populates="action_logs")
