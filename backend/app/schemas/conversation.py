from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class CallTurnResponse(BaseModel):
    id: str
    call_session_id: str
    turn_index: int
    step_key: str
    agent_prompt: str
    patient_audio_transcript: Optional[str] = None
    detected_language: Optional[str] = None
    intent: Optional[str] = None
    extracted_entities: Dict[str, Any] = {}
    repeated_count: int
    was_unanswered: bool
    created_at: datetime

    class Config:
        from_attributes = True

class CallSessionResponse(BaseModel):
    id: str
    patient_id: str
    direction: str
    call_type: str
    status: str
    disposition: Optional[str] = None
    language_used: str
    current_step_key: str
    interrupted_at: Optional[datetime] = None
    resume_context: Dict[str, Any] = {}
    is_deferred: bool
    deferred_until: Optional[datetime] = None
    deferral_reason: Optional[str] = None
    retry_count: int
    duration_seconds: int
    caller_phone: Optional[str] = None
    audio_url: Optional[str] = None
    transferred_to_human: bool
    transfer_reason: Optional[str] = None
    callback_requested: bool
    created_at: datetime
    updated_at: datetime
    turns: List[CallTurnResponse] = []

    class Config:
        from_attributes = True

class StartCallRequest(BaseModel):
    patient_id: str
    call_type: str = "MORNING_CHECKIN" # MORNING_CHECKIN, EVENING_CHECKIN, MEDICATION_REMINDER, APPOINTMENT_REMINDER
    direction: str = "OUTBOUND"
    language: Optional[str] = None # mr, hi, en (falls back to patient.preferred_language)
    caller_phone: Optional[str] = None

class ProcessTurnRequest(BaseModel):
    session_id: str
    user_speech_text: str # Transcript from STT or live web simulator input
    audio_data_base64: Optional[str] = None # Optional voice audio chunk

class ProcessTurnResponse(BaseModel):
    session_id: str
    turn_index: int
    step_key: str
    agent_prompt_text: str
    language: str
    audio_url: Optional[str] = None
    is_completed: bool
    is_transferred: bool = False
    is_red_flag: bool = False
    disposition: Optional[str] = None
    extracted_data: Dict[str, Any] = {}
    next_step_key: Optional[str] = None

class InterruptionResumeRequest(BaseModel):
    session_id: str

class CallDispositionRequest(BaseModel):
    disposition: str # COMPLETED, PARTIAL, NO_ANSWER, BUSY, UNREACHABLE, WRONG_PERSON, DECLINED, DISCONNECTED
    notes: Optional[str] = None
