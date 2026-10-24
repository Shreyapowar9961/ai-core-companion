from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class EscalationRuleCreate(BaseModel):
    code: str
    name: str
    category: str # VITALS, SYMPTOMS, TREND, MEDICATION, CONTACT_FAILURE, COMPOSITE_DECLINE
    severity: str # CRITICAL, HIGH, MEDIUM, INFO
    condition_json: Dict[str, Any]
    action_json: Dict[str, Any]
    is_active: bool = True
    facility_id: Optional[str] = None

class EscalationRuleResponse(BaseModel):
    id: str
    code: str
    name: str
    category: str
    severity: str
    condition_json: Dict[str, Any]
    action_json: Dict[str, Any]
    is_active: bool
    facility_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AlertActionLogResponse(BaseModel):
    id: str
    alert_id: str
    user_id: str
    user_name: str
    action: str
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AlertResponse(BaseModel):
    id: str
    patient_id: str
    rule_id: Optional[str] = None
    rule_code: str
    severity: str
    title: str
    description: str
    supporting_data: Dict[str, Any]
    status: str
    sla_due_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_action_notes: Optional[str] = None
    caregiver_notified: bool
    caregiver_ack_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    action_logs: List[AlertActionLogResponse] = []

    class Config:
        from_attributes = True

class AlertAcknowledgeRequest(BaseModel):
    notes: Optional[str] = None

class AlertResolveRequest(BaseModel):
    resolution_action_notes: str # Required explicit closure with clinical action (DB-04, ES-07)
