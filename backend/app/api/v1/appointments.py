from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, verify_patient_access
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.schemas.appointment import (
    AppointmentCreate, AppointmentUpdate, AppointmentConfirmRequest,
    AppointmentRescheduleRequest, AppointmentResponse
)
from app.core.audit import log_audit_event

router = APIRouter(prefix="/appointments", tags=["Follow-up Appointments"])

@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    req: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, req.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    appt = Appointment(
        patient_id=req.patient_id,
        appointment_type=req.appointment_type,
        scheduled_time=req.scheduled_time,
        doctor_facility_name=req.doctor_facility_name,
        location=req.location,
        preparation_instructions=req.preparation_instructions,
        status="SCHEDULED"
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    log_audit_event(
        db=db,
        event_type="APPOINTMENT_CREATED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="appointment",
        details={"appointment_id": appt.id, "type": appt.appointment_type},
        patient_id=req.patient_id
    )

    return appt

@router.get("/patient/{patient_id}", response_model=List[AppointmentResponse])
def list_patient_appointments(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    stmt = select(Appointment).where(
        Appointment.patient_id == patient_id
    ).order_by(Appointment.scheduled_time)
    return db.execute(stmt).scalars().all()

@router.post("/{appointment_id}/confirm", response_model=AppointmentResponse)
def confirm_appointment_attendance(
    appointment_id: str,
    req: AppointmentConfirmRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appt.status = req.status
    if req.status == "CONFIRMED":
        appt.attendance_confirmed_at = datetime.utcnow()
    elif req.status == "DECLINED":
        appt.decline_reason = req.reason

    db.commit()
    db.refresh(appt)

    log_audit_event(
        db=db,
        event_type="APPOINTMENT_ATTENDANCE_CONFIRMED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="appointment",
        details={"status": req.status, "reason": req.reason},
        patient_id=appt.patient_id
    )

    return appt

@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule_appointment(
    appointment_id: str,
    req: AppointmentRescheduleRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appt.status = "RESCHEDULE_REQUESTED"
    appt.reschedule_reason = req.reason
    appt.reschedule_task_created = True
    appt.reschedule_notes = f"Patient requested reschedule. Preferred time: {req.preferred_time}. Reason: {req.reason}"

    if req.preferred_time:
        appt.scheduled_time = req.preferred_time
        appt.status = "SCHEDULED"

    db.commit()
    db.refresh(appt)

    log_audit_event(
        db=db,
        event_type="APPOINTMENT_RESCHEDULE_REQUESTED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="appointment",
        details={"reason": req.reason, "preferred_time": str(req.preferred_time)},
        patient_id=appt.patient_id
    )

    return appt

@router.get("/patient/{patient_id}/next")
def get_next_appointment(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    stmt = select(Appointment).where(
        Appointment.patient_id == patient_id,
        Appointment.scheduled_time >= datetime.utcnow(),
        Appointment.status != "DECLINED"
    ).order_by(Appointment.scheduled_time).limit(1)
    appt = db.execute(stmt).scalars().first()

    if not appt:
        return {"has_appointment": False, "message": "No upcoming appointments scheduled."}

    return {
        "has_appointment": True,
        "appointment_id": appt.id,
        "appointment_type": appt.appointment_type,
        "scheduled_time": appt.scheduled_time.isoformat(),
        "doctor_facility_name": appt.doctor_facility_name,
        "location": appt.location,
        "preparation_instructions": appt.preparation_instructions,
        "status": appt.status
    }
