from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AppointmentCreate(BaseModel):
    patient_id: str
    appointment_type: str = "DOCTOR_FOLLOWUP" # DOCTOR_FOLLOWUP, LAB_TEST, PHYSIOTHERAPY
    scheduled_time: datetime
    doctor_facility_name: str
    location: Optional[str] = None
    preparation_instructions: Optional[str] = None

class AppointmentUpdate(BaseModel):
    appointment_type: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    doctor_facility_name: Optional[str] = None
    location: Optional[str] = None
    preparation_instructions: Optional[str] = None
    status: Optional[str] = None
    decline_reason: Optional[str] = None

class AppointmentConfirmRequest(BaseModel):
    # CONFIRMED, DECLINED, UNCERTAIN (AP-02)
    status: str
    reason: Optional[str] = None

class AppointmentRescheduleRequest(BaseModel):
    # AP-03: Reschedule request
    preferred_time: Optional[datetime] = None
    reason: str

class AppointmentResponse(BaseModel):
    id: str
    patient_id: str
    appointment_type: str
    scheduled_time: datetime
    doctor_facility_name: str
    location: Optional[str] = None
    preparation_instructions: Optional[str] = None
    status: str
    attendance_confirmed_at: Optional[datetime] = None
    decline_reason: Optional[str] = None
    reschedule_reason: Optional[str] = None
    reschedule_task_created: bool
    reschedule_notes: Optional[str] = None
    missed_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
