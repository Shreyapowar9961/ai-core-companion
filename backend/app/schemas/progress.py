from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date

class DailyProgressScoreResponse(BaseModel):
    id: str
    patient_id: str
    score_date: date
    medication_score: float
    checkin_score: float
    hydration_score: float
    activity_score: float
    overall_score: float
    is_declining: bool
    declining_indicators: List[str]
    calculation_breakdown: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True

class ProgressTrendPoint(BaseModel):
    date: str
    overall_score: float
    medication_score: float
    checkin_score: float
    hydration_score: float
    activity_score: float

class PatientTrendViewResponse(BaseModel):
    patient_id: str
    days: int # 7 or 30 (PR-04, PR-05)
    average_adherence: float
    average_progress_score: float
    is_declining_pattern: bool
    data_points: List[ProgressTrendPoint]

class PatientSummaryResponse(BaseModel):
    id: str
    patient_id: str
    summary_date: date
    summary_type: str
    language: str
    content: str
    delivered_via: str
    is_delivered: bool
    created_at: datetime

    class Config:
        from_attributes = True
