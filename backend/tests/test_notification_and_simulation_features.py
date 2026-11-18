"""
Tests for Feature A (Notification Read/Unread), Feature F (Retry Scheduling),
Feature G (Multilingual Phrasing), and Feature I (Email Service Interface).

Strictly ₹0 local testing against MockPostgresSession.
PostgreSQL ONLY. ZERO SQLite.
"""

import pytest
from datetime import datetime, date, timedelta
from fastapi import HTTPException

from app.models.patient import Patient
from app.models.monitoring import CommunicationLog, CheckinTask
from app.models.conversation import CallSession
from app.models.clinical import MedicationSchedule
from app.core.security import AuthUser, UserRole
from app.api.v1.patient_portal import (
    get_patient_notifications,
    get_unread_notification_count,
    mark_notification_read,
    mark_all_notifications_read
)
from app.services.conversation_service import ConversationService
from app.services.monitoring_scheduler import format_checkin_notification, format_medication_reminder
from app.services.email_service import EmailService
from tests.mock_db import MockPostgresSession


@pytest.fixture
def portal_setup():
    db = MockPostgresSession()

    patient1 = Patient(
        id="pt-notif-1",
        first_name="Ramesh",
        last_name="Patil",
        dob=date(1965, 8, 12),
        gender="Male",
        phone="+919820011111",
        preferred_language="hi",
        retry_limit=3,
        status="ACTIVE"
    )
    db.add(patient1)

    patient2 = Patient(
        id="pt-notif-2",
        first_name="Sunita",
        last_name="Devi",
        dob=date(1970, 3, 20),
        gender="Female",
        phone="+919820022222",
        preferred_language="mr",
        retry_limit=2,
        status="ACTIVE"
    )
    db.add(patient2)

    user1 = AuthUser(
        id="usr-p1",
        email="ramesh@care.org",
        role=UserRole.PATIENT,
        patient_id="pt-notif-1",
        name="Ramesh Patil"
    )

    user2 = AuthUser(
        id="usr-p2",
        email="sunita@care.org",
        role=UserRole.PATIENT,
        patient_id="pt-notif-2",
        name="Sunita Devi"
    )

    # Patient 1 notifications (2 unread, 1 read)
    notif1 = CommunicationLog(
        id="notif-1",
        patient_id="pt-notif-1",
        channel="SIMULATED_SMS",
        message_type="RECOVERY_CHECKIN",
        content="Namaste Ramesh, recovery checkin is due.",
        status="DELIVERED",
        is_simulated=True,
        sent_at=datetime.utcnow() - timedelta(hours=2),
        viewed_at=None
    )
    notif2 = CommunicationLog(
        id="notif-2",
        patient_id="pt-notif-1",
        channel="SIMULATED_WHATSAPP",
        message_type="MEDICATION_REMINDER",
        content="Time to take your Aspirin.",
        status="DELIVERED",
        is_simulated=True,
        sent_at=datetime.utcnow() - timedelta(hours=1),
        viewed_at=None
    )
    notif3 = CommunicationLog(
        id="notif-3",
        patient_id="pt-notif-1",
        channel="SIMULATED_VOICE",
        message_type="FOLLOWUP_REMINDER",
        content="Followup call scheduled.",
        status="VIEWED",
        is_simulated=True,
        sent_at=datetime.utcnow() - timedelta(days=1),
        viewed_at=datetime.utcnow() - timedelta(hours=20)
    )

    # Patient 2 notification
    notif4 = CommunicationLog(
        id="notif-4",
        patient_id="pt-notif-2",
        channel="SIMULATED_WHATSAPP",
        message_type="RECOVERY_CHECKIN",
        content="Namaskar Sunita, checkin is due.",
        status="DELIVERED",
        is_simulated=True,
        sent_at=datetime.utcnow(),
        viewed_at=None
    )

    db.add_all([notif1, notif2, notif3, notif4])
    return db, patient1, patient2, user1, user2, notif1, notif2, notif3, notif4


# =============================================================================
# FEATURE A: NOTIFICATION READ/UNREAD TESTS
# =============================================================================

def test_get_patient_notifications_includes_read_state(portal_setup):
    db, p1, p2, u1, u2, n1, n2, n3, n4 = portal_setup
    result = get_patient_notifications(current_user=u1, db=db)
    
    assert len(result) == 3
    # Find n1 and n3
    n1_res = next(item for item in result if item["id"] == "notif-1")
    n3_res = next(item for item in result if item["id"] == "notif-3")

    assert n1_res["is_read"] is False
    assert n1_res["viewed_at"] is None

    assert n3_res["is_read"] is True
    assert n3_res["viewed_at"] is not None


def test_unread_notification_count(portal_setup):
    db, p1, p2, u1, u2, n1, n2, n3, n4 = portal_setup
    
    # Patient 1 has 2 unread
    res1 = get_unread_notification_count(current_user=u1, db=db)
    assert res1["unread_count"] == 2

    # Patient 2 has 1 unread
    res2 = get_unread_notification_count(current_user=u2, db=db)
    assert res2["unread_count"] == 1


def test_mark_individual_notification_read(portal_setup):
    db, p1, p2, u1, u2, n1, n2, n3, n4 = portal_setup
    
    res = mark_notification_read(notification_id="notif-1", current_user=u1, db=db)
    assert res["is_read"] is True
    assert res["status"] == "VIEWED"
    assert res["viewed_at"] is not None

    # Unread count should now be 1
    unread = get_unread_notification_count(current_user=u1, db=db)
    assert unread["unread_count"] == 1


def test_cross_patient_notification_access_blocked(portal_setup):
    """Patient 1 cannot read or mark Patient 2's notification (Anti-IDOR)."""
    db, p1, p2, u1, u2, n1, n2, n3, n4 = portal_setup
    
    with pytest.raises(HTTPException) as exc:
        mark_notification_read(notification_id="notif-4", current_user=u1, db=db)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Notification not found."


def test_mark_all_notifications_read(portal_setup):
    db, p1, p2, u1, u2, n1, n2, n3, n4 = portal_setup
    
    res = mark_all_notifications_read(current_user=u1, db=db)
    assert res["status"] == "SUCCESS"
    assert res["marked_read_count"] == 2

    unread = get_unread_notification_count(current_user=u1, db=db)
    assert unread["unread_count"] == 0

    # Patient 2's unread notifications must remain unread
    p2_unread = get_unread_notification_count(current_user=u2, db=db)
    assert p2_unread["unread_count"] == 1


# =============================================================================
# FEATURE F: FOLLOW-UP RETRY SCHEDULING TESTS
# =============================================================================

def test_retry_scheduling_bounded_backoff(portal_setup):
    db, p1, p2, u1, u2, n1, n2, n3, n4 = portal_setup

    session = CallSession(
        id="call-sess-1",
        patient_id=p1.id,
        status="IN_PROGRESS",
        retry_count=0
    )
    db.add(session)

    # Attempt 1 failed with NO_ANSWER -> 15 min backoff
    res1 = ConversationService.handle_call_disposition(
        db=db,
        session_id=session.id,
        disposition="NO_ANSWER",
        is_simulation=True
    )
    assert res1["status"] == "RETRY_SCHEDULED"
    assert res1["retry_count"] == 1
    assert res1["backoff_minutes"] == 15
    assert session.is_deferred is True

    # Attempt 2 failed with BUSY -> 45 min backoff
    res2 = ConversationService.handle_call_disposition(
        db=db,
        session_id=session.id,
        disposition="BUSY",
        is_simulation=True
    )
    assert res2["status"] == "RETRY_SCHEDULED"
    assert res2["retry_count"] == 2
    assert res2["backoff_minutes"] == 45

    # Attempt 3 failed with UNREACHABLE -> reaches retry limit (3)
    res3 = ConversationService.handle_call_disposition(
        db=db,
        session_id=session.id,
        disposition="UNREACHABLE",
        is_simulation=True
    )
    assert res3["status"] == "FAILED"
    assert res3["retry_count"] == 3
    assert res3["retry_limit"] == 3
    assert session.status == "FAILED"
    assert session.is_deferred is False


# =============================================================================
# FEATURE G: MULTILINGUAL NOTIFICATION PHRASING TESTS
# =============================================================================

def test_multilingual_checkin_notification(portal_setup):
    db, p1, p2, u1, u2, n1, n2, n3, n4 = portal_setup

    # Patient 1 is Hindi (preferred_language = "hi")
    msg_hi = format_checkin_notification(p1)
    assert "Namaste Ramesh" in msg_hi
    assert "dainik recovery check-in taiyar hai" in msg_hi

    # Patient 2 is Marathi (preferred_language = "mr")
    msg_mr = format_checkin_notification(p2)
    assert "Namaskar Sunita" in msg_mr
    assert "dainik recovery check-in tayar ahe" in msg_mr


def test_multilingual_medication_reminder(portal_setup):
    db, p1, p2, u1, u2, n1, n2, n3, n4 = portal_setup

    med = MedicationSchedule(
        id="med-sch-1",
        patient_id=p1.id,
        medicine_name="Atorvastatin",
        dosage="40mg",
        instructions="Take at night after food",
        is_active=True
    )

    # Hindi formatting preserves exact medicine and dosage
    msg_hi = format_medication_reminder(p1, med)
    assert "Atorvastatin (40mg)" in msg_hi
    assert "Dawa Reminder" in msg_hi

    # Marathi formatting
    msg_mr = format_medication_reminder(p2, med)
    assert "Atorvastatin (40mg)" in msg_mr
    assert "Aushadh Reminder" in msg_mr


# =============================================================================
# FEATURE I: EMAIL SERVICE INTERFACE & TEMPLATES
# =============================================================================

def test_email_template_rendering():
    email = EmailService.render_followup_email(
        patient_name="Ramesh Patil",
        hospital_name="Apex Heart Institute",
        days_post_op=3
    )
    assert "Day 3 Post-Discharge" in email["subject"]
    assert "Ramesh Patil" in email["text"]
    assert "Apex Heart Institute" in email["html"]
    assert "Complete Recovery Check-in" in email["html"]


def test_email_service_safe_pending_configuration():
    """Confirms email service safely returns PENDING_CONFIGURATION when disabled."""
    result = EmailService.send_email(
        recipient_email="patient@example.com",
        subject="Recovery Check-in",
        text_content="Please complete your check-in"
    )
    assert result["success"] is False
    assert result["status"] == "PENDING_CONFIGURATION"
    assert result["is_simulated"] is True
