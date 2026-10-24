from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date

class FacilityBase(BaseModel):
    name: str
    location: Optional[str] = None
    contact_phone: Optional[str] = None

class FacilityCreate(FacilityBase):
    pass

class FacilityResponse(FacilityBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class CaregiverBase(BaseModel):
    name: str
    relationship: str
    phone: str
    email: Optional[str] = None
    is_authorized: bool = True
    consented_channels: List[str] = ["SMS", "WHATSAPP", "VOICE"]
    consented_categories: List[str] = ["medication", "vitals", "alerts", "appointments"]

class CaregiverCreate(CaregiverBase):
    pass

class CaregiverResponse(CaregiverBase):
    id: str
    patient_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class ConsentBase(BaseModel):
    voice_contact: bool = False
    call_recording: bool = False
    data_processing: bool = False
    caregiver_disclosure: bool = False
    emergency_escalation: bool = False
    consent_notes: Optional[str] = None

class ConsentCreate(ConsentBase):
    pass

class ConsentResponse(ConsentBase):
    id: str
    patient_id: str
    consented_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    withdrawal_scope: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConsentWithdrawRequest(BaseModel):
    # FULL, CAREGIVER_ONLY, CALLS_ONLY (PL-03, PL-04)
    scope: str = "FULL"
    reason: Optional[str] = None

class MedicationScheduleInput(BaseModel):
    medicine_name: str
    dosage: str
    frequency: str = "Once daily"
    dose_times: List[str] = ["09:00"]
    instructions: Optional[str] = None
    route: str = "Oral"

class VitalsThresholdInput(BaseModel):
    vital_type: str # BP_SYSTOLIC, BP_DIASTOLIC, BLOOD_GLUCOSE, SPO2, TEMPERATURE, PULSE, WEIGHT
    unit: str
    plausible_min: float
    plausible_max: float
    normal_min: Optional[float] = None
    normal_max: Optional[float] = None
    warning_min: Optional[float] = None
    warning_max: Optional[float] = None
    critical_min: Optional[float] = None
    critical_max: Optional[float] = None

class CarePlanCreate(BaseModel):
    diet_instructions: Optional[str] = None
    hydration_target_glasses: int = 8
    hydration_interval_hours: int = 2
    activity_target_minutes: int = 20
    activity_target_steps: int = 2000
    physiotherapy_instructions: Optional[str] = None
    medications: List[MedicationScheduleInput] = []
    vitals_thresholds: List[VitalsThresholdInput] = []

class PatientRegisterRequest(BaseModel):
    # Demographics (ON-01)
    facility_id: Optional[str] = None
    first_name: str
    last_name: str
    dob: date
    gender: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    
    # Discharge Details (ON-01)
    diagnosis: str
    discharge_date: date
    programme_duration_days: int = 30
    preferred_language: str = "en" # mr, hi, en (LN-01)
    
    # Operational configuration (ON-05)
    call_window_start: str = "09:00"
    call_window_end: str = "19:00"
    checkin_morning_time: str = "09:30"
    checkin_evening_time: str = "18:30"
    dnd_start: str = "21:00"
    dnd_end: str = "08:00"
    retry_limit: int = 3
    max_deferrals: int = 2
    
    # Treating Doctor (ON-03)
    treating_doctor_name: Optional[str] = None
    treating_doctor_phone: Optional[str] = None
    treating_doctor_specialty: Optional[str] = None
    
    # Caregivers (ON-03)
    caregivers: List[CaregiverCreate] = []
    
    # Care Plan (ON-02)
    care_plan: Optional[CarePlanCreate] = None
    
    # Explicit Consent (ON-04)
    consent: Optional[ConsentCreate] = None
    
    # Activate immediately if valid (ON-06)
    activate_if_complete: bool = True

class PatientUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    preferred_language: Optional[str] = None
    call_window_start: Optional[str] = None
    call_window_end: Optional[str] = None
    checkin_morning_time: Optional[str] = None
    checkin_evening_time: Optional[str] = None
    dnd_start: Optional[str] = None
    dnd_end: Optional[str] = None
    retry_limit: Optional[int] = None
    max_deferrals: Optional[int] = None

class PatientResponse(BaseModel):
    id: str
    facility_id: Optional[str] = None
    first_name: str
    last_name: str
    dob: date
    gender: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    diagnosis: str
    discharge_date: date
    programme_duration_days: int
    preferred_language: str
    status: str
    paused_at: Optional[datetime] = None
    pause_reason: Optional[str] = None
    completed_at: Optional[datetime] = None
    call_window_start: str
    call_window_end: str
    checkin_morning_time: str
    checkin_evening_time: str
    dnd_start: str
    dnd_end: str
    retry_limit: int
    max_deferrals: int
    treating_doctor_name: Optional[str] = None
    treating_doctor_phone: Optional[str] = None
    treating_doctor_specialty: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    caregivers: List[CaregiverResponse] = []
    consent: Optional[ConsentResponse] = None

    class Config:
        from_attributes = True

class PatientPauseResumeRequest(BaseModel):
    reason: Optional[str] = None
