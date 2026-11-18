import os
import base64
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Dict, Any, List, Optional

from app.core.database import get_db
from app.core.security import get_current_user, AuthUser, UserRole
from app.core.audit import log_audit_event
from app.models.conversation import CallSession, CallTurn
from app.models.patient import Consent
from app.services.conversation_service import ConversationService
from app.services.rules_engine import RulesEngine
from app.schemas.conversation import (
    StartCallRequest, ProcessTurnRequest, ProcessTurnResponse,
    InterruptionResumeRequest, CallDispositionRequest, CallSessionResponse
)

AUDIO_STORAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "uploads",
    "audio_recordings"
)
os.makedirs(AUDIO_STORAGE_DIR, exist_ok=True)

router = APIRouter(prefix="/conversation", tags=["Voice Conversation Engine"])

@router.post("/start", response_model=Dict[str, Any])
@router.post("/sessions/initiate", response_model=Dict[str, Any])
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
        if req.language or req.initial_language:
            session.language_used = req.language or req.initial_language
            db.commit()

        prompt, step = ConversationService.get_initial_prompt(db, session)
        return {
            "session_id": session.id,
            "id": session.id,
            "patient_id": session.patient_id,
            "status": session.status,
            "current_step": step,
            "current_step_key": step,
            "initial_prompt": prompt,
            "initial_prompt_text": prompt,
            "language": session.language_used
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@router.post("/turn", response_model=ProcessTurnResponse)
@router.post("/turns/process", response_model=ProcessTurnResponse)
def process_turn(
    req: ProcessTurnRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    try:
        speech = req.user_speech_text or req.user_speech or ""
        result = ConversationService.process_turn(
            db=db,
            session_id=req.session_id,
            user_speech=speech
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

@router.post("/sessions/{session_id}/resume", response_model=Dict[str, Any])
def resume_interrupted_call_path(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    try:
        return ConversationService.resume_interrupted_session(db, session_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

@router.get("/patient/{patient_id}/calls", response_model=List[CallSessionResponse])
def get_patient_calls(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    stmt = select(CallSession).where(CallSession.patient_id == patient_id).order_by(CallSession.created_at.desc())
    return db.execute(stmt).scalars().all()

@router.post("/sessions/{session_id}/disposition")
def record_disposition(
    session_id: str,
    req: CallDispositionRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    try:
        return ConversationService.handle_call_disposition(
            db=db,
            session_id=session_id,
            disposition=req.disposition,
            is_simulation=req.is_simulation,
            notes=req.notes
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

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


@router.post("/sessions/{session_id}/audio")
async def upload_call_audio(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """
    CV-08: Consent-controlled browser audio upload for simulated calls.
    Subject to patient recording consent (GV-02). Securely persists audio in local backend storage.
    """
    session = db.get(CallSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")

    # Consent verification (CV-08, GV-02)
    consent = db.execute(
        select(Consent).where(Consent.patient_id == session.patient_id)
    ).scalars().first()

    if consent and not consent.call_recording:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Call recording is prohibited because patient withheld recording consent (CV-08, GV-02)."
        )

    file_bytes = b""
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded_file = form.get("audio_file") or form.get("file")
        if uploaded_file and hasattr(uploaded_file, "read"):
            file_bytes = await uploaded_file.read()
    elif "application/json" in content_type:
        body = await request.json()
        b64_data = body.get("audio_base64") or body.get("audio_data_base64")
        if b64_data:
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            file_bytes = base64.b64decode(b64_data)
    else:
        file_bytes = await request.body()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="No audio data received in payload")

    audio_path = os.path.join(AUDIO_STORAGE_DIR, f"{session_id}.webm")
    with open(audio_path, "wb") as f:
        f.write(file_bytes)

    session.audio_url = f"/api/v1/conversation/sessions/{session_id}/audio/stream"
    db.commit()

    log_audit_event(
        db=db,
        event_type="CALL_AUDIO_RECORDED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="call_session",
        details={
            "session_id": session_id,
            "patient_id": session.patient_id,
            "audio_size_bytes": len(file_bytes),
            "storage_path": f"uploads/audio_recordings/{session_id}.webm"
        },
        patient_id=session.patient_id
    )

    return {
        "success": True,
        "session_id": session_id,
        "audio_url": session.audio_url,
        "size_bytes": len(file_bytes),
        "status": "RECORDED"
    }


@router.get("/sessions/{session_id}/audio")
@router.get("/sessions/{session_id}/audio/stream")
def stream_call_audio(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    """
    CV-08: Authenticated audio streaming for clinicians to review call recordings.
    """
    session = db.get(CallSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")

    audio_path = os.path.join(AUDIO_STORAGE_DIR, f"{session_id}.webm")
    if not os.path.isfile(audio_path):
        raise HTTPException(status_code=404, detail="Audio recording file not found on disk")

    log_audit_event(
        db=db,
        event_type="CALL_AUDIO_ACCESSED",
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        resource="call_session",
        details={
            "session_id": session_id,
            "patient_id": session.patient_id
        },
        patient_id=session.patient_id
    )

    return FileResponse(
        audio_path,
        media_type="audio/webm",
        filename=f"call_{session_id}.webm"
    )
