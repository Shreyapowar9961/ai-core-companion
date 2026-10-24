from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Dict, Any, List

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser
from app.models.conversation import CallSession, CallTurn
from app.services.conversation_service import ConversationService
from app.services.rules_engine import RulesEngine
from app.schemas.conversation import (
    StartCallRequest, ProcessTurnRequest, ProcessTurnResponse,
    InterruptionResumeRequest, CallDispositionRequest, CallSessionResponse
)

router = APIRouter(prefix="/conversation", tags=["Voice Conversation Engine"])

@router.post("/start", response_model=Dict[str, Any])
def start_call(
    req: StartCallRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    try:
        session = ConversationService.initiate_session(
            db=db,
            patient_id=req.patient_id,
            call_type=req.call_type,
            direction=req.direction,
            caller_phone=req.caller_phone
        )
        prompt, step = ConversationService.get_initial_prompt(db, session)
        return {
            "session_id": session.id,
            "patient_id": session.patient_id,
            "status": session.status,
            "current_step": step,
            "initial_prompt": prompt,
            "language": session.language_used
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.post("/turn", response_model=ProcessTurnResponse)
def process_turn(
    req: ProcessTurnRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    try:
        result = ConversationService.process_turn(
            db=db,
            session_id=req.session_id,
            user_speech=req.user_speech_text
        )
        return ProcessTurnResponse(
            session_id=result["session_id"],
            turn_index=result["turn_index"],
            step_key=result["step_key"],
            agent_prompt_text=result["agent_prompt_text"],
            language=result["language"],
            is_completed=result["is_completed"],
            is_transferred=result.get("is_transferred", False),
            is_red_flag=result.get("is_red_flag", False),
            disposition=result.get("disposition"),
            extracted_data=result.get("extracted_data", {}),
            next_step_key=result.get("next_step_key")
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.post("/resume", response_model=Dict[str, Any])
def resume_interrupted_call(
    req: InterruptionResumeRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    try:
        return ConversationService.resume_interrupted_session(db, req.session_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.post("/sessions/{session_id}/disposition")
def record_disposition(
    session_id: str,
    req: CallDispositionRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    session = db.get(CallSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.disposition = req.disposition
    session.status = "COMPLETED" if req.disposition == "COMPLETED" else "FAILED"
    db.commit()

    if req.disposition in ["NO_ANSWER", "BUSY", "UNREACHABLE", "DECLINED"]:
        session.retry_count += 1
        db.commit()
        RulesEngine.evaluate_contact_failure(
            db=db,
            patient_id=session.patient_id,
            retry_count=session.retry_count,
            retry_limit=3,
            last_disposition=req.disposition
        )

    return {"message": "Disposition recorded", "session_id": session.id, "disposition": req.disposition}

@router.get("/sessions/{session_id}", response_model=CallSessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    session = db.get(CallSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
