from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, UserRole, require_roles
from app.models.audit import AuditLog, ConfigAuditLog
from app.core.audit import reconstruct_patient_journey

router = APIRouter(prefix="/audit", tags=["Lifecycle, Governance & Audit Trail"])

@router.get("/logs")
async def list_audit_logs(
    patient_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    """
    GV-03: Maintain an immutable audit trail of calls, reminders, responses,
    confirmations, alerts, escalations, handoffs, consent and access.
    """
    stmt = select(AuditLog)
    if patient_id:
        stmt = stmt.where(AuditLog.patient_id == patient_id)
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    stmt = stmt.order_by(desc(AuditLog.created_at)).limit(limit)

    logs = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": l.id,
            "event_type": l.event_type,
            "actor_id": l.actor_id,
            "actor_role": l.actor_role,
            "patient_id": l.patient_id,
            "resource": l.resource,
            "details": l.details_json,
            "created_at": l.created_at.isoformat()
        }
        for l in logs
    ]

@router.get("/config-logs")
async def list_config_audit_logs(
    config_type: Optional[str] = None,
    item_id: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    """
    GV-04: Log all configuration changes to schedules, thresholds,
    questionnaires, rules and content, with previous and new values.
    """
    stmt = select(ConfigAuditLog)
    if config_type:
        stmt = stmt.where(ConfigAuditLog.config_type == config_type)
    if item_id:
        stmt = stmt.where(ConfigAuditLog.item_id == item_id)
    stmt = stmt.order_by(desc(ConfigAuditLog.created_at)).limit(limit)

    logs = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": l.id,
            "config_type": l.config_type,
            "item_id": l.item_id,
            "changed_by": l.changed_by,
            "old_value": l.old_value_json,
            "new_value": l.new_value_json,
            "change_reason": l.change_reason,
            "created_at": l.created_at.isoformat()
        }
        for l in logs
    ]

@router.get("/journey/{patient_id}")
async def get_patient_interaction_journey(
    patient_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(require_roles([UserRole.CLINICIAN, UserRole.ADMIN]))
):
    """
    GV-05: Enable reconstruction of a patient's complete interaction history
    for any period by an authorised user.
    """
    journey = await reconstruct_patient_journey(
        db=db,
        patient_id=patient_id,
        start_date=start_date,
        end_date=end_date
    )
    return {
        "patient_id": patient_id,
        "total_events": len(journey),
        "events": journey
    }
