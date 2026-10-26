from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, verify_patient_access
from app.models.patient import Patient
from app.schemas.progress import (
    DailyProgressScoreResponse, PatientTrendViewResponse, PatientSummaryResponse
)
from app.services.progress_service import ProgressService

router = APIRouter(prefix="/progress", tags=["Progress & Recovery Reporting"])

@router.get("/patient/{patient_id}/today", response_model=DailyProgressScoreResponse)
@router.get("/today/{patient_id}", response_model=DailyProgressScoreResponse)
def get_today_progress_score(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    score = ProgressService.calculate_daily_progress_score(db, patient_id)
    return score

@router.get("/patient/{patient_id}/trends", response_model=PatientTrendViewResponse)
@router.get("/patient/{patient_id}/history", response_model=PatientTrendViewResponse)
@router.get("/history/{patient_id}", response_model=PatientTrendViewResponse)
def get_progress_trends(
    patient_id: str,
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    return ProgressService.get_patient_trend_view(db, patient_id, days=days)

@router.post("/patient/{patient_id}/eod-summary", response_model=PatientSummaryResponse)
def deliver_patient_eod_summary(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    return ProgressService.generate_end_of_day_voice_summary(db, patient_id)

@router.post("/patient/{patient_id}/caregiver-summary", response_model=PatientSummaryResponse)
def deliver_caregiver_summary(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    verify_patient_access(patient_id, current_user, patient.facility_id)

    summary = ProgressService.generate_caregiver_summary(db, patient_id)
    if not summary:
        raise HTTPException(status_code=400, detail="No authorized caregiver found for this patient.")
    return summary
