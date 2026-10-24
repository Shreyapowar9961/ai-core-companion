from fastapi import APIRouter, Depends, Request, Response, Form, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import base64

from app.core.database import get_db
from app.services.telephony.twilio_adapter import TwilioCallChannel
from app.services.conversation_service import ConversationService
from app.models.conversation import CallSession

router = APIRouter(prefix="/telephony", tags=["Telephony Provider Integration"])

twilio_channel = TwilioCallChannel()

@router.post("/twilio/webhook")
async def twilio_webhook(
    request: Request,
    session_id: Optional[str] = Query(None),
    lang: Optional[str] = Query("en"),
    SpeechResult: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Twilio Voice Webhook: receives speech input from <Gather> and returns dynamic TwiML.
    """
    if not session_id:
        # Initial greeting TwiML
        twiml = await twilio_channel.generate_response(
            session_id="new_session",
            prompt_text="Hello, this is your AI Care Companion.",
            language=lang or "en",
            gather_speech=True
        )
        return Response(content=twiml, media_type="application/xml")

    # If speech was recognized by Twilio STT
    user_speech = SpeechResult or ""
    result = await ConversationService.process_turn(
        db=db,
        session_id=session_id,
        user_speech=user_speech
    )

    twiml = await twilio_channel.generate_response(
        session_id=session_id,
        prompt_text=result["agent_prompt_text"],
        language=result["language"],
        gather_speech=not result["is_completed"],
        next_step=result.get("next_step_key")
    )
    return Response(content=twiml, media_type="application/xml")

@router.post("/twilio/status")
async def twilio_status_callback(
    request: Request,
    session_id: Optional[str] = Query(None),
    CallStatus: Optional[str] = Form(None),
    CallDuration: Optional[int] = Form(0),
    db: AsyncSession = Depends(get_db)
):
    """
    Twilio Call Status Webhook: tracks initiated, ringing, answered, completed, busy, no-answer.
    """
    if session_id:
        session = await db.get(CallSession, session_id)
        if session:
            status_map = {
                "completed": "COMPLETED",
                "busy": "BUSY",
                "no-answer": "NO_ANSWER",
                "failed": "UNREACHABLE",
                "canceled": "DECLINED"
            }
            session.disposition = status_map.get(CallStatus, "PARTIAL")
            session.status = "COMPLETED" if CallStatus == "completed" else "FAILED"
            session.duration_seconds = CallDuration or session.duration_seconds
            await db.commit()

    return {"status": "ok"}

@router.get("/audio-stream")
async def get_synthetic_audio(
    lang: str = "en",
    text: Optional[str] = None
):
    """
    Audio generation endpoint for browser testing and speech verification.
    Returns standard audio stream header.
    """
    # 1-second silent MP3 audio header bytes for zero-error offline client playback
    silent_mp3_base64 = "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//OEAAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAAFAAAAZgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
    return Response(content=base64.b64decode(silent_mp3_base64), media_type="audio/mp3")
