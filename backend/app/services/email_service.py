"""
AI Care Companion — Email Service Interface & Template Engine.
Implements safe ₹0 provider interface for automated post-discharge follow-ups.
Real delivery remains DISABLED until company approval and provider credentials are provided.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger("email-service")

class EmailService:
    """
    Healthcare email interface supporting provider abstraction (Resend / Brevo).
    Operates safely in simulation / pending-configuration mode when credentials are not configured.
    """

    @classmethod
    def render_followup_email(
        cls,
        patient_name: str,
        hospital_name: str = "Apex Heart Institute",
        portal_url: str = "https://care.apexcare.org/portal",
        days_post_op: int = 1
    ) -> Dict[str, str]:
        subject = f"[{hospital_name}] Day {days_post_op} Post-Discharge Recovery Follow-up"
        text_body = (
            f"Dear {patient_name},\n\n"
            f"This is an automated recovery follow-up from {hospital_name}.\n"
            f"Please complete today's recovery check-in by logging into your patient portal:\n"
            f"{portal_url}\n\n"
            "If you are experiencing severe chest pain, extreme breathlessness, or surgical site complications, "
            "contact emergency care immediately or call your clinic.\n\n"
            "Warm regards,\n"
            f"Post-Discharge Recovery Team\n{hospital_name}"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; rounded: 8px;">
            <h2 style="color: #4338ca;">{hospital_name}</h2>
            <p>Dear <strong>{patient_name}</strong>,</p>
            <p>This is your scheduled Day {days_post_op} post-discharge recovery follow-up.</p>
            <p>Please report your daily recovery vitals and symptom check-in:</p>
            <p style="margin: 24px 0;">
                <a href="{portal_url}" style="background-color: #4f46e5; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Complete Recovery Check-in</a>
            </p>
            <p style="font-size: 12px; color: #64748b; margin-top: 32px; border-top: 1px solid #e2e8f0; padding-top: 12px;">
                Safety Notice: This message is part of your monitored recovery plan. In case of emergency, contact hospital triage or dial 112/911 immediately.
            </p>
        </div>
        """
        return {"subject": subject, "text": text_body, "html": html_body}

    @classmethod
    def render_medication_reminder_email(
        cls,
        patient_name: str,
        medicine_name: str,
        dosage: str,
        instructions: str,
        portal_url: str = "https://care.apexcare.org/portal"
    ) -> Dict[str, str]:
        subject = f"Medication Reminder: Time to take your {medicine_name}"
        text_body = (
            f"Dear {patient_name},\n\n"
            f"This is a reminder to take your scheduled dose of {medicine_name} ({dosage}).\n"
            f"Instructions: {instructions}\n\n"
            f"Please confirm intake in your portal: {portal_url}\n\n"
            "Apex Heart Institute Recovery Team"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; rounded: 8px;">
            <h3 style="color: #4338ca;">Medication Reminder</h3>
            <p>Dear <strong>{patient_name}</strong>,</p>
            <p>It is time to take your prescribed dose of:</p>
            <div style="background-color: #f8fafc; border-left: 4px solid #4f46e5; padding: 12px; margin: 16px 0;">
                <p style="margin: 0; font-weight: bold; font-size: 16px;">{medicine_name} ({dosage})</p>
                <p style="margin: 4px 0 0 0; color: #64748b; font-size: 14px;">Instructions: {instructions}</p>
            </div>
            <p><a href="{portal_url}" style="background-color: #4f46e5; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">Confirm Intake in Portal</a></p>
        </div>
        """
        return {"subject": subject, "text": text_body, "html": html_body}

    @classmethod
    def send_email(
        cls,
        recipient_email: str,
        subject: str,
        text_content: str,
        html_content: Optional[str] = None,
        patient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends email via configured free-tier provider (Resend / Brevo).
        If credentials are not supplied, returns explicit PENDING_CONFIGURATION status
        without falsely claiming delivery.
        """
        # Strict ₹0 Safety Guard: Check if live provider credentials exist
        resend_key = getattr(settings, "RESEND_API_KEY", None)
        brevo_key = getattr(settings, "BREVO_API_KEY", None)
        email_enabled = getattr(settings, "EMAIL_ENABLED", False)

        if not email_enabled or (not resend_key and not brevo_key):
            logger.info(
                f"[EMAIL_SERVICE] Real email dispatch disabled (Pending Credentials). "
                f"Recipient: {recipient_email}, Subject: '{subject}'"
            )
            return {
                "success": False,
                "status": "PENDING_CONFIGURATION",
                "provider": "NONE",
                "recipient": recipient_email,
                "message": "Real email delivery is disabled pending approved provider credentials (Resend or Brevo).",
                "is_simulated": True
            }

        # If credentials were provided in the future, dispatch here safely
        # (Kept disabled by default per project specification)
        return {
            "success": False,
            "status": "DISABLED_BY_POLICY",
            "message": "Outbound email delivery disabled by policy until explicit user activation."
        }
