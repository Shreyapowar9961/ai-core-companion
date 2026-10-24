from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date

class MedicationScheduleCreate(BaseModel):
    care_plan_id: str
    medicine_name: str
    dosage: str
    frequency: str = "Once daily"
    dose_times: List[str] = ["09:00"]
    instructions: Optional[str] = None
    route: str = "Oral"
    effective_start_date: date = Field(default_factory=date.today)
    effective_end_date: Optional[date] = None

class MedicationScheduleResponse(BaseModel):
    id: str
    care_plan_id: str
    patient_id: str
    medicine_name: str
    dosage: str
    frequency: str
    dose_times: List[str]
    instructions: Optional[str] = None
    route: str
    effective_start_date: date
    effective_end_date: Optional[date] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class MedicationLogCreate(BaseModel):
    medication_schedule_id: Optional[str] = None
    medicine_name: str
    dosage: Optional[str] = None
    scheduled_time: datetime
    actual_time: Optional[datetime] = None
    status: str = "TAKEN" # TAKEN, MISSED, PENDING, DEFERRED
    stated_reason: Optional[str] = None
    deferral_count: int = 0
    recorded_via: str = "VOICE_CALL"

class MedicationLogResponse(BaseModel):
    id: str
    patient_id: str
    medication_schedule_id: Optional[str] = None
    medicine_name: str
    dosage: Optional[str] = None
    scheduled_time: datetime
    actual_time: Optional[datetime] = None
    status: str
    stated_reason: Optional[str] = None
    deferral_count: int
    recorded_via: str
    created_at: datetime

    class Config:
        from_attributes = True

class VitalsThresholdResponse(BaseModel):
    id: str
    care_plan_id: str
    patient_id: str
    vital_type: str
    unit: str
    plausible_min: float
    plausible_max: float
    normal_min: Optional[float] = None
    normal_max: Optional[float] = None
    warning_min: Optional[float] = None
    warning_max: Optional[float] = None
    critical_min: Optional[float] = None
    critical_max: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

class VitalReadingCreate(BaseModel):
    vital_type: str
    value: Optional[float] = None
    secondary_value: Optional[float] = None
    unit: str
    voice_confirmed: bool = True
    call_session_id: Optional[str] = None
    notes: Optional[str] = None

class VitalReadingResponse(BaseModel):
    id: str
    patient_id: str
    call_session_id: Optional[str] = None
    vital_type: str
    value: Optional[float] = None
    secondary_value: Optional[float] = None
    unit: str
    status: str # NORMAL, WARNING, CRITICAL, NOT_PROVIDED, IMPLAUSIBLE
    voice_confirmed: bool
    notes: Optional[str] = None
    recorded_at: datetime

    class Config:
        from_attributes = True

class SymptomCheckinCreate(BaseModel):
    call_session_id: Optional[str] = None
    checkin_type: str = "MORNING" # MORNING, EVENING
    pain_level: int = 0 # 0-10
    weakness: str = "none" # none, mild, moderate, severe
    dizziness: str = "none"
    breathlessness: str = "none"
    swelling: str = "none"
    fever: str = "none"
    wound_status: str = "healing_well" # healing_well, redness, discharge, pain
    appetite: str = "normal" # normal, reduced, none
    sleep_quality: str = "good" # good, fair, poor
    other_symptoms_verbatim: Optional[str] = None
    other_symptoms_structured: Dict[str, Any] = {}
    comparison_with_yesterday: Dict[str, str] = {}

class SymptomCheckinResponse(BaseModel):
    id: str
    patient_id: str
    call_session_id: Optional[str] = None
    checkin_type: str
    pain_level: int
    weakness: str
    dizziness: str
    breathlessness: str
    swelling: str
    fever: str
    wound_status: str
    appetite: str
    sleep_quality: str
    other_symptoms_verbatim: Optional[str] = None
    other_symptoms_structured: Dict[str, Any]
    comparison_with_yesterday: Dict[str, str]
    recorded_at: datetime

    class Config:
        from_attributes = True

class LifestyleLogCreate(BaseModel):
    log_type: str # HYDRATION, ACTIVITY, PHYSIOTHERAPY, MEAL
    target_value: Optional[float] = None
    actual_value: Optional[float] = None
    unit: Optional[str] = None
    completion_status: str = "COMPLETED" # COMPLETED, PARTIAL, MISSED
    reported_pain_difficulty: Optional[str] = None
    notes: Optional[str] = None

class LifestyleLogResponse(BaseModel):
    id: str
    patient_id: str
    log_type: str
    target_value: Optional[float] = None
    actual_value: Optional[float] = None
    unit: Optional[str] = None
    completion_status: str
    reported_pain_difficulty: Optional[str] = None
    notes: Optional[str] = None
    recorded_at: datetime

    class Config:
        from_attributes = True
