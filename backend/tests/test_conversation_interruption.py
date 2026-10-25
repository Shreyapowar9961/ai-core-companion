import pytest
from datetime import date, datetime
from app.models.patient import Patient, Consent, CarePlan
from app.models.conversation import CallSession, CallTurn
from app.services.conversation_service import ConversationService
from backend.tests.mock_db import MockPostgresSession

def test_call_interruption_and_resumption():
    """
    CM-05: On call disconnection, persist all captured data and resume
    from the point of interruption rather than restarting.
    Zero SQLite.
    """
    db = MockPostgresSession()
    p = Patient(
        id="test-interrupt-pt",
        first_name="Mahesh",
        last_name="Bhosale",
        dob=date(1958, 2, 10),
        gender="Male",
        phone="+919833001122",
        diagnosis="Post-Stent",
        discharge_date=date.today(),
        status="ACTIVE",
        preferred_language="en"
    )
    db.add(p)
    c = Consent(
        patient_id=p.id,
        voice_contact=True,
        call_recording=True,
        data_processing=True
    )
    db.add(c)

    session = ConversationService.initiate_session(
        db=db,
        patient_id="test-interrupt-pt",
        call_type="MORNING_CHECKIN"
    )

    # Turn 1: Caller verification
    t1 = ConversationService.process_turn(
        db=db,
        session_id=session.id,
        user_speech="Yes, I am Mahesh speaking."
    )
    assert t1["next_step_key"] == "WELLBEING"

    # Turn 2: Wellbeing
    t2 = ConversationService.process_turn(
        db=db,
        session_id=session.id,
        user_speech="I am feeling okay this morning."
    )
    assert t2["next_step_key"] == "SYMPTOMS_PAIN"

    # Turn 3: Pain reported
    t3 = ConversationService.process_turn(
        db=db,
        session_id=session.id,
        user_speech="Mild pain in chest, around 3 out of 10."
    )
    assert t3["next_step_key"] == "SYMPTOMS_BREATHLESSNESS"

    # SIMULATE CALL DISCONNECTION AT THIS POINT!
    session.status = "INTERRUPTED"
    session.disposition = "DISCONNECTED"
    session.interrupted_at = datetime.utcnow()
    db.commit()

    # Verify context was persisted
    assert session.current_step_key == "SYMPTOMS_BREATHLESSNESS"
    assert session.resume_context.get("pain_level") == 3

    # RESUME CALL: Must resume from SYMPTOMS_BREATHLESSNESS, NOT restart from Turn 1!
    resumed = ConversationService.resume_interrupted_session(db, session.id)
    assert resumed["resumed_at_step"] == "SYMPTOMS_BREATHLESSNESS"
    assert resumed["saved_context"]["pain_level"] == 3
    assert "where we left off" in resumed["agent_prompt_text"]

def test_human_transfer_request():
    """
    CV-07: Transfer to a human care-team member on request or protocol trigger.
    """
    db = MockPostgresSession()
    p = Patient(
        id="test-interrupt-pt-2",
        first_name="Mahesh",
        last_name="Bhosale",
        dob=date(1958, 2, 10),
        gender="Male",
        phone="+919833001122",
        diagnosis="Post-Stent",
        discharge_date=date.today(),
        status="ACTIVE",
        preferred_language="en"
    )
    db.add(p)
    c = Consent(
        patient_id=p.id,
        voice_contact=True,
        call_recording=True,
        data_processing=True
    )
    db.add(c)

    session = ConversationService.initiate_session(
        db=db,
        patient_id="test-interrupt-pt-2",
        call_type="MORNING_CHECKIN"
    )

    t = ConversationService.process_turn(
        db=db,
        session_id=session.id,
        user_speech="Please connect me to a doctor or nurse right now."
    )

    assert t["is_transferred"] is True
    assert t["is_completed"] is True
    assert session.transferred_to_human is True
