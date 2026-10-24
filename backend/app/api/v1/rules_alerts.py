from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, UserRole, require_roles
from app.models.rules_alert import EscalationRule, Alert, AlertActionLog
from app.models.patient import Patient
from app.schemas.rules_alert import (
    EscalationRuleCreate, EscalationRuleResponse, AlertResponse,
    AlertAcknowledgeRequest, AlertResolveRequest
)
from app.core.audit import log_audit_event, log_config_audit

router = APIRouter(prefix="/rules-alerts", tags=["Rules Engine & Escalation"])

@router.get("/rules", response_model=List[EscalationRuleResponse])
def list_rules(
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    stmt = select(EscalationRule).order_by(EscalationRule.severity, EscalationRule.code)
    return db.execute(stmt).scalars().all()

@router.post("/rules", response_model=EscalationRuleResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_rule(
    req: EscalationRuleCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    stmt = select(EscalationRule).where(EscalationRule.code == req.code)
    rule = db.execute(stmt).scalars().first()

    old_val = None
    if not rule:
        rule = EscalationRule(
            code=req.code,
            name=req.name,
            category=req.category,
            severity=req.severity,
            condition_json=req.condition_json,
            action_json=req.action_json,
            is_active=req.is_active,
            facility_id=req.facility_id
        )
        db.add(rule)
    else:
        old_val = {"condition": rule.condition_json, "action": rule.action_json, "severity": rule.severity}
        rule.name = req.name
        rule.category = req.category
        rule.severity = req.severity
        rule.condition_json = req.condition_json
        rule.action_json = req.action_json
        rule.is_active = req.is_active

    db.commit()
    db.refresh(rule)

    log_config_audit(
        db=db,
        config_type="RULE",
        item_id=rule.id,
        changed_by=current_user.id,
        old_value=old_val,
        new_value=req.dict(),
        change_reason="Clinician rule configuration update"
    )

    return rule

@router.get("/alerts", response_model=List[AlertResponse])
def list_alerts(
    patient_id: Optional[str] = None,
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    stmt = select(Alert)
    if patient_id:
        stmt = stmt.where(Alert.patient_id == patient_id)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter)
    stmt = stmt.order_by(desc(Alert.created_at)).limit(limit)

    return db.execute(stmt).scalars().all()

@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: str,
    req: AlertAcknowledgeRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = datetime.utcnow()
    alert.acknowledged_by = f"{current_user.name} ({current_user.role.value})"

    action_log = AlertActionLog(
        alert_id=alert.id,
        user_id=current_user.id,
        user_name=current_user.name,
        action="ACKNOWLEDGED",
        notes=req.notes or "Alert acknowledged within clinical SLA window"
    )
    db.add(action_log)
    db.commit()
    db.refresh(alert)

    log_audit_event(
        db=db,
        event_type="ALERT_ACKNOWLEDGED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="alert",
        details={"alert_id": alert.id, "severity": alert.severity},
        patient_id=alert.patient_id
    )

    return alert

@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: str,
    req: AlertResolveRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if not req.resolution_action_notes or len(req.resolution_action_notes.strip()) < 5:
        raise HTTPException(status_code=400, detail="Explicit clinical action notes required for resolution closure")

    alert.status = "RESOLVED"
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = f"{current_user.name} ({current_user.role.value})"
    alert.resolution_action_notes = req.resolution_action_notes

    action_log = AlertActionLog(
        alert_id=alert.id,
        user_id=current_user.id,
        user_name=current_user.name,
        action="RESOLVED",
        notes=req.resolution_action_notes
    )
    db.add(action_log)
    db.commit()
    db.refresh(alert)

    log_audit_event(
        db=db,
        event_type="ALERT_RESOLVED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="alert",
        details={"alert_id": alert.id, "action_notes": req.resolution_action_notes},
        patient_id=alert.patient_id
    )

    return alert
