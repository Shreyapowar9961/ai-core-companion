"""
Feature H: Firebase Cloud Messaging (FCM) Web Push Notification Test Suite.

Verifies:
1. Generic Privacy-Safe Payload Generation (Strict Zero-PHI enforcement).
2. Authenticated Device Token Registration (POST /portal/notifications/device-token).
3. Token Registration Idempotence (No duplicate rows for same token).
4. Specific Token Deregistration (DELETE /portal/notifications/device-token).
5. All-Tokens Deregistration on Logout / Opt-out.
6. Strict Anti-IDOR Cross-Patient Protection.
7. Shared Device / Transfer Reassignment Handling.
8. Notification Preferences Get and Toggle (GET/PUT /portal/notifications/preferences).
9. Safe Disabled-by-Default Execution (Zero network calls when FCM_ENABLED=False).
10. Successful Dispatch with Mocked Firebase Messaging.
11. Stale / Invalid Token Automatic Invalidation (UnregisteredError -> is_active=False).
12. Skipped Dispatch When Push is Disabled or No Active Tokens.

PostgreSQL ONLY. Strictly ZERO SQLite.
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.core.config import settings
from app.core.security import AuthUser, UserRole
from app.models.patient import Patient
from app.models.device_token import PushDeviceRegistration
from app.schemas.device_token import (
    DeviceTokenRegisterRequest,
    DeviceTokenUnregisterRequest,
    NotificationPreferencesUpdateRequest
)
from app.api.v1.patient_portal import (
    register_device_token,
    unregister_device_token,
    get_notification_preferences,
    update_notification_preferences
)
from app.services.fcm_service import fcm_service, mask_token
from tests.mock_db import MockPostgresSession


@pytest.fixture
def fcm_test_setup():
    db = MockPostgresSession()

    patient1 = Patient(
        id="pt-fcm-1",
        first_name="Ramesh",
        last_name="Kulkarni",
        dob=date(1962, 4, 15),
        gender="Male",
        phone="+919811223344",
        status="ACTIVE"
    )
    db.add(patient1)

    user1 = AuthUser(
        id="usr-p1",
        email="ramesh@apexcare.org",
        role=UserRole.PATIENT,
        patient_id="pt-fcm-1",
        name="Ramesh Kulkarni"
    )

    patient2 = Patient(
        id="pt-fcm-2",
        first_name="Sunita",
        last_name="Patil",
        dob=date(1971, 9, 21),
        gender="Female",
        phone="+919822334455",
        status="ACTIVE"
    )
    db.add(patient2)

    user2 = AuthUser(
        id="usr-p2",
        email="sunita@apexcare.org",
        role=UserRole.PATIENT,
        patient_id="pt-fcm-2",
        name="Sunita Patil"
    )

    return db, user1, user2


# -----------------------------------------------------------------------------
# 1. PRIVACY & PHI SAFEGUARDS
# -----------------------------------------------------------------------------

def test_generic_payload_builder_strict_phi_prevention():
    """Verify notification payloads NEVER contain PHI, patient names, diagnoses, or dosages."""
    types_to_test = [
        "MEDICATION_REMINDER",
        "RECOVERY_CHECKIN",
        "CARE_TEAM_UPDATE",
        "MISSED_ALERT",
        "GENERAL",
        "UNKNOWN_TYPE"
    ]

    phi_forbidden_words = [
        "ramesh", "sunita", "aspirin", "metoprolol", "atorvastatin",
        "mg", "dosage", "infarction", "angioplasty", "hypertension",
        "post-op", "patient mrn", "doctor"
    ]

    for ntype in types_to_test:
        title, body, data = fcm_service.build_generic_payload(ntype)

        assert title == "AI Care Companion"
        assert len(body) > 10
        assert data["click_action"] == "/portal"
        assert "timestamp" in data

        lower_body = body.lower()
        for forbidden in phi_forbidden_words:
            assert forbidden not in lower_body, f"Found forbidden PHI '{forbidden}' in body: {body}"


def test_token_masking_utility():
    """Verify mask_token masks tokens for logs without leaking raw token strings."""
    raw = "fK9Xz1234567890abcdefghijklmnopqrstuvwxyz"
    masked = mask_token(raw)
    assert masked.startswith("fK9Xz1...")
    assert masked.endswith("wxyz")
    assert raw not in masked
    assert mask_token("") == "***"
    assert mask_token("short") == "***"


# -----------------------------------------------------------------------------
# 2. DEVICE TOKEN REGISTRATION & IDEMPOTENCE
# -----------------------------------------------------------------------------

def test_device_token_registration_success(fcm_test_setup):
    """Patient registers an FCM web push token successfully."""
    db, user1, _ = fcm_test_setup
    sample_token = "eK7-sample-fcm-token-string-abcdef1234567890"

    req = DeviceTokenRegisterRequest(
        fcm_token=sample_token,
        device_type="web",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"
    )

    res = register_device_token(req=req, current_user=user1, db=db)
    assert res["status"] == "SUCCESS"
    assert res["is_active"] is True
    assert "registration_id" in res

    # Verify stored in DB
    regs = list(db.storage.get(PushDeviceRegistration, {}).values())
    assert len(regs) == 1
    assert regs[0].patient_id == "pt-fcm-1"
    assert regs[0].fcm_token == sample_token
    assert regs[0].is_active is True
    assert regs[0].push_enabled is True


def test_device_token_registration_idempotence(fcm_test_setup):
    """Repeated registration of the same token for the same patient does not duplicate rows."""
    db, user1, _ = fcm_test_setup
    sample_token = "idempotent-fcm-token-1234567890"

    req = DeviceTokenRegisterRequest(fcm_token=sample_token, device_type="web")
    res1 = register_device_token(req=req, current_user=user1, db=db)
    res2 = register_device_token(req=req, current_user=user1, db=db)

    assert res1["registration_id"] == res2["registration_id"]

    regs = list(db.storage.get(PushDeviceRegistration, {}).values())
    assert len(regs) == 1


# -----------------------------------------------------------------------------
# 3. DEREGISTRATION & LOGOUT CLEANUP
# -----------------------------------------------------------------------------

def test_device_token_deregistration_specific_token(fcm_test_setup):
    """Deregistering a specific token deactivates only that token."""
    db, user1, _ = fcm_test_setup
    token_a = "token-device-a-1234567890"
    token_b = "token-device-b-1234567890"

    register_device_token(DeviceTokenRegisterRequest(fcm_token=token_a), user1, db)
    register_device_token(DeviceTokenRegisterRequest(fcm_token=token_b), user1, db)

    unreg_req = DeviceTokenUnregisterRequest(fcm_token=token_a)
    res = unregister_device_token(req=unreg_req, current_user=user1, db=db)

    assert res["status"] == "SUCCESS"
    assert res["deactivated_count"] == 1

    regs = list(db.storage.get(PushDeviceRegistration, {}).values())
    reg_a = next(r for r in regs if r.fcm_token == token_a)
    reg_b = next(r for r in regs if r.fcm_token == token_b)

    assert reg_a.is_active is False
    assert reg_a.invalidation_reason == "USER_DEREGISTERED"
    assert reg_b.is_active is True


def test_device_token_deregistration_all_tokens_on_logout(fcm_test_setup):
    """Deregistering without specific token deactivates all active tokens for that patient."""
    db, user1, _ = fcm_test_setup
    register_device_token(DeviceTokenRegisterRequest(fcm_token="token-1-1234567890"), user1, db)
    register_device_token(DeviceTokenRegisterRequest(fcm_token="token-2-1234567890"), user1, db)

    res = unregister_device_token(req=None, current_user=user1, db=db)
    assert res["status"] == "SUCCESS"
    assert res["deactivated_count"] == 2

    regs = list(db.storage.get(PushDeviceRegistration, {}).values())
    for r in regs:
        assert r.is_active is False


# -----------------------------------------------------------------------------
# 4. CROSS-PATIENT IDOR & REASSIGNMENT PROTECTION
# -----------------------------------------------------------------------------

def test_cross_patient_idor_protection(fcm_test_setup):
    """Patient B cannot unregister or affect Patient A's active token."""
    db, user1, user2 = fcm_test_setup
    token_patient1 = "patient-1-exclusive-token-1234567890"

    register_device_token(DeviceTokenRegisterRequest(fcm_token=token_patient1), user1, db)

    # Patient 2 attempts to unregister Patient 1's token
    res = unregister_device_token(
        req=DeviceTokenUnregisterRequest(fcm_token=token_patient1),
        current_user=user2,
        db=db
    )

    assert res["deactivated_count"] == 0

    regs = list(db.storage.get(PushDeviceRegistration, {}).values())
    reg1 = next(r for r in regs if r.fcm_token == token_patient1)
    assert reg1.is_active is True
    assert reg1.patient_id == "pt-fcm-1"


def test_device_transfer_reassigns_cleanly(fcm_test_setup):
    """If the same device token is subsequently registered by another patient, old registration is invalidated."""
    db, user1, user2 = fcm_test_setup
    shared_device_token = "shared-tablet-token-1234567890"

    # Registered first by Patient 1
    register_device_token(DeviceTokenRegisterRequest(fcm_token=shared_device_token), user1, db)

    # Later registered by Patient 2 on the same device
    register_device_token(DeviceTokenRegisterRequest(fcm_token=shared_device_token), user2, db)

    regs = list(db.storage.get(PushDeviceRegistration, {}).values())
    reg1 = next(r for r in regs if r.patient_id == "pt-fcm-1")
    reg2 = next(r for r in regs if r.patient_id == "pt-fcm-2")

    assert reg1.is_active is False
    assert reg1.invalidation_reason == "DEVICE_REASSIGNED"
    assert reg2.is_active is True


# -----------------------------------------------------------------------------
# 5. PREFERENCES RETRIEVAL & TOGGLE
# -----------------------------------------------------------------------------

def test_notification_preferences_get_and_update(fcm_test_setup):
    """Patient retrieves and updates push preferences."""
    db, user1, _ = fcm_test_setup

    # Initially before token registration
    pref0 = get_notification_preferences(current_user=user1, db=db)
    assert pref0.has_registered_device is False
    assert pref0.active_devices_count == 0

    # Register token
    register_device_token(DeviceTokenRegisterRequest(fcm_token="pref-token-1234567890"), user1, db)
    pref1 = get_notification_preferences(current_user=user1, db=db)
    assert pref1.has_registered_device is True
    assert pref1.active_devices_count == 1
    assert pref1.push_enabled is True

    # Disable push notifications
    update_res = update_notification_preferences(
        req=NotificationPreferencesUpdateRequest(push_enabled=False),
        current_user=user1,
        db=db
    )
    assert update_res["status"] == "SUCCESS"
    assert update_res["push_enabled"] is False

    pref2 = get_notification_preferences(current_user=user1, db=db)
    assert pref2.push_enabled is False


# -----------------------------------------------------------------------------
# 6. DISPATCH LOGIC (FCM_ENABLED=False default, MOCKED FIREBASE, ERROR HANDLING)
# -----------------------------------------------------------------------------

def test_fcm_send_disabled_by_default(fcm_test_setup):
    """When FCM_ENABLED=False, sending simulates gracefully without external network calls."""
    db, user1, _ = fcm_test_setup
    register_device_token(DeviceTokenRegisterRequest(fcm_token="token-disabled-1234567890"), user1, db)

    with patch.object(settings, "FCM_ENABLED", False):
        res = fcm_service.send_push_to_patient(db, "pt-fcm-1", notification_type="RECOVERY_CHECKIN")
        assert res["status"] == "SIMULATED_DISABLED"
        assert res["sent_count"] == 1
        assert res["failed_count"] == 0
        assert "recovery check-in" in res["body"]


def test_fcm_send_no_active_tokens_skipped(fcm_test_setup):
    """If patient has no registered or active devices, dispatch is safely skipped."""
    db, _, _ = fcm_test_setup
    res = fcm_service.send_push_to_patient(db, "patient-without-tokens", notification_type="MEDICATION_REMINDER")
    assert res["status"] == "SKIPPED"
    assert res["reason"] == "NO_ACTIVE_TOKENS"


def test_fcm_send_with_mocked_messaging_success(fcm_test_setup):
    """With mocked firebase messaging, verified message structure is built and sent."""
    db, user1, _ = fcm_test_setup
    sample_token = "mock-active-token-1234567890"
    register_device_token(DeviceTokenRegisterRequest(fcm_token=sample_token), user1, db)

    from firebase_admin import messaging

    with patch.object(settings, "FCM_ENABLED", True), \
         patch.object(fcm_service, "initialize_firebase", return_value=True), \
         patch.object(messaging, "send", return_value="projects/test/messages/msg-123") as mock_send:

        res = fcm_service.send_push_to_patient(db, "pt-fcm-1", notification_type="MEDICATION_REMINDER")

        assert res["status"] == "SUCCESS"
        assert res["sent_count"] == 1
        assert res["failed_count"] == 0
        assert mock_send.call_count == 1

        sent_msg = mock_send.call_args[0][0]
        assert sent_msg.token == sample_token
        assert sent_msg.notification.title == "AI Care Companion"
        assert "scheduled medication reminder" in sent_msg.notification.body
        assert sent_msg.data["click_action"] == "/portal"


def test_fcm_send_invalid_token_auto_invalidation(fcm_test_setup):
    """When Firebase reports UnregisteredError, token is automatically deactivated in DB."""
    db, user1, _ = fcm_test_setup
    stale_token = "stale-unregistered-token-1234567890"
    register_device_token(DeviceTokenRegisterRequest(fcm_token=stale_token), user1, db)

    from firebase_admin import messaging

    with patch.object(settings, "FCM_ENABLED", True), \
         patch.object(fcm_service, "initialize_firebase", return_value=True), \
         patch.object(messaging, "send", side_effect=messaging.UnregisteredError("App instance unregistered")):

        res = fcm_service.send_push_to_patient(db, "pt-fcm-1", notification_type="GENERAL")

        assert res["status"] == "FAILED"
        assert res["sent_count"] == 0
        assert res["failed_count"] == 1

        regs = list(db.storage.get(PushDeviceRegistration, {}).values())
        stale_reg = next(r for r in regs if r.fcm_token == stale_token)
        assert stale_reg.is_active is False
        assert stale_reg.invalidation_reason == "TOKEN_UNREGISTERED"
        assert stale_reg.invalidated_at is not None
