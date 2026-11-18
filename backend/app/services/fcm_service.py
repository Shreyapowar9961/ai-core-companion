import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.models.device_token import PushDeviceRegistration

logger = logging.getLogger("fcm_service")


def mask_token(token: Optional[str]) -> str:
    """Safely masks FCM token for audit and debug logging."""
    if not token or len(token) < 10:
        return "***"
    return f"{token[:6]}...{token[-4:]}"


class FCMService:
    """
    Firebase Cloud Messaging Web Push Notification Service.
    - Implements strict PHI safeguards (strictly generic messages).
    - Manages token lifecycles and automatic invalidation.
    - Guarded by settings.FCM_ENABLED (disabled by default).
    - ₹0 budget: Firebase Spark tier compatible.
    """

    def __init__(self):
        self._initialized = False
        self._firebase_app = None

    def _resolve_credentials_path(self) -> Optional[str]:
        raw_path = settings.GOOGLE_APPLICATION_CREDENTIALS or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not raw_path:
            return None

        candidates = [
            raw_path,
            raw_path + ".json" if not raw_path.endswith(".json") else raw_path + ".json",
            r"D:\firebase-secrets\firebase-admin.json",
            r"D:\firebase-secrets\firebase-admin.json.json",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def initialize_firebase(self) -> bool:
        """
        Initializes Firebase Admin SDK app safely if enabled.
        Returns True if initialized or already active, False if disabled/missing credentials.
        """
        if not settings.FCM_ENABLED:
            logger.info("FCM is disabled by configuration (FCM_ENABLED=False).")
            return False

        if self._initialized:
            return True

        try:
            import firebase_admin
            from firebase_admin import credentials

            # Check if default app already exists
            if firebase_admin._apps:
                self._firebase_app = firebase_admin.get_app()
                self._initialized = True
                return True

            cred_path = self._resolve_credentials_path()
            if not cred_path:
                logger.warning("FCM initialization skipped: GOOGLE_APPLICATION_CREDENTIALS path not found.")
                return False

            cred = credentials.Certificate(cred_path)
            self._firebase_app = firebase_admin.initialize_app(
                cred,
                {"projectId": settings.FIREBASE_PROJECT_ID}
            )
            self._initialized = True
            logger.info("Firebase Admin SDK initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            return False

    @staticmethod
    def build_generic_payload(notification_type: str = "GENERAL") -> Tuple[str, str, Dict[str, str]]:
        """
        Builds strictly generic, privacy-safe notification payload.
        NEVER includes patient names, diagnoses, medication names, dosages, or PHI.
        """
        title = "AI Care Companion"
        normalized = (notification_type or "").upper()

        if normalized == "MEDICATION_REMINDER":
            body = "You have a scheduled medication reminder. Please check your patient portal."
        elif normalized == "RECOVERY_CHECKIN":
            body = "Your daily recovery check-in is ready. Open your patient portal."
        elif normalized == "CARE_TEAM_UPDATE":
            body = "Your care team has posted an update. Open your patient portal."
        elif normalized == "MISSED_ALERT":
            body = "A recovery reminder requires your attention. Open your patient portal."
        else:
            body = "You have a new recovery reminder. Open your patient portal."

        data = {
            "click_action": "/portal",
            "notification_type": normalized,
            "timestamp": datetime.utcnow().isoformat()
        }
        return title, body, data

    def send_push_to_patient(
        self,
        db: Session,
        patient_id: str,
        notification_type: str = "GENERAL"
    ) -> Dict[str, Any]:
        """
        Sends generic push notification to all active registered devices for a patient.
        Automatically marks invalid or unregistered tokens as inactive in PostgreSQL.
        """
        # Fetch active tokens with push enabled
        tokens = db.execute(
            select(PushDeviceRegistration).where(
                PushDeviceRegistration.patient_id == patient_id,
                PushDeviceRegistration.is_active == True,
                PushDeviceRegistration.push_enabled == True
            )
        ).scalars().all()

        if not tokens:
            return {
                "status": "SKIPPED",
                "sent_count": 0,
                "failed_count": 0,
                "reason": "NO_ACTIVE_TOKENS"
            }

        title, body, data = self.build_generic_payload(notification_type)

        # If FCM is globally disabled, log and return safe response without external network calls
        if not settings.FCM_ENABLED:
            logger.info(
                f"FCM disabled: Simulating push notification to {len(tokens)} device(s) for patient {patient_id}."
            )
            return {
                "status": "SIMULATED_DISABLED",
                "sent_count": len(tokens),
                "failed_count": 0,
                "title": title,
                "body": body
            }

        if not self.initialize_firebase():
            return {
                "status": "ERROR_NOT_INITIALIZED",
                "sent_count": 0,
                "failed_count": len(tokens),
                "reason": "FIREBASE_NOT_CONFIGURED"
            }

        try:
            import firebase_admin
            from firebase_admin import messaging
            from firebase_admin.exceptions import FirebaseError
        except ImportError:
            logger.error("firebase-admin package not available.")
            return {"status": "ERROR_IMPORT", "sent_count": 0, "failed_count": len(tokens)}

        sent_count = 0
        failed_count = 0
        now = datetime.utcnow()

        for reg in tokens:
            try:
                # Use WebpushConfig for web notifications
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=data,
                    token=reg.fcm_token,
                    webpush=messaging.WebpushConfig(
                        fcm_options=messaging.WebpushFCMOptions(
                            link="/portal"
                        ),
                        notification=messaging.WebpushNotification(
                            title=title,
                            body=body,
                            icon="/vite.svg",
                        )
                    )
                )

                response = messaging.send(message)
                logger.info(f"FCM message sent successfully to {mask_token(reg.fcm_token)}: {response}")
                reg.last_sent_at = now
                sent_count += 1
            except (messaging.UnregisteredError, messaging.SenderIdMismatchError) as e:
                logger.warning(f"FCM token unregistered/stale: {mask_token(reg.fcm_token)}. Deactivating. ({e})")
                reg.is_active = False
                reg.invalidated_at = now
                reg.invalidation_reason = "TOKEN_UNREGISTERED"
                failed_count += 1
            except messaging.InvalidArgumentError as e:
                logger.warning(f"FCM invalid token argument: {mask_token(reg.fcm_token)}. Deactivating. ({e})")
                reg.is_active = False
                reg.invalidated_at = now
                reg.invalidation_reason = "INVALID_ARGUMENT"
                failed_count += 1
            except Exception as e:
                logger.error(f"FCM send failed for token {mask_token(reg.fcm_token)}: {e}")
                failed_count += 1

        db.commit()
        return {
            "status": "SUCCESS" if sent_count > 0 else "FAILED",
            "sent_count": sent_count,
            "failed_count": failed_count
        }


fcm_service = FCMService()
