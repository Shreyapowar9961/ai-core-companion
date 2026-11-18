import os
import re
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)
load_dotenv()


def mask_database_url(url_or_msg: str) -> str:
    """
    Safely masks database credentials, passwords, and tokens in connection
    strings or error messages to prevent leakage in application logs.
    """
    if not url_or_msg:
        return ""
    # Mask password in URI pattern: scheme://user:password@host...
    masked = re.sub(r"://([^:@\s]+):([^@\s]+)@", r"://\1:***@", str(url_or_msg))
    # Mask password/token in query or key-value parameters
    masked = re.sub(r"(password|token|secret)=([^\s;&]+)", r"\1=***", masked, flags=re.IGNORECASE)
    return masked


def is_loopback_host(url: str) -> bool:
    """
    Checks if a given database URL targets localhost or loopback address.
    """
    if not url:
        return False
    host_part = url.split("@")[-1] if "@" in url else url
    host_clean = host_part.split("/")[0].split("?")[0].lower()
    return any(lb in host_clean for lb in ("localhost", "127.0.0.1", "::1", "0.0.0.0"))


class Settings(BaseModel):
    PROJECT_NAME: str = "AI Care Companion"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Host
    ENVIRONMENT: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    BACKEND_PORT: int = Field(default_factory=lambda: int(os.getenv("BACKEND_PORT", "8000")))
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ]
    
    # Database: Strictly PostgreSQL and Supabase
    POSTGRES_USER: str = Field(default_factory=lambda: os.getenv("POSTGRES_USER", "postgres"))
    POSTGRES_PASSWORD: str = Field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD", "postgres"))
    POSTGRES_SERVER: str = Field(default_factory=lambda: os.getenv("POSTGRES_SERVER", "localhost"))
    POSTGRES_PORT: str = Field(default_factory=lambda: os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = Field(default_factory=lambda: os.getenv("POSTGRES_DB", "ai_care_companion_test"))

    DATABASE_URL: Optional[str] = None
    SYNC_DATABASE_URL: Optional[str] = None

    def validate_production_database_config(self) -> None:
        """
        Explicitly validates production database configuration.
        Ensures explicit Supabase URLs, PostgreSQL drivers, and loopback prevention.
        Rejects generated URLs from POSTGRES_* fallback variables.
        Never reveals passwords or sensitive secrets.
        """
        if not self.DATABASE_URL or not self.DATABASE_URL.strip():
            raise ValueError(
                "Production configuration error: Explicit DATABASE_URL environment variable is required. "
                "Constructing connection URLs from POSTGRES_* fallback variables is prohibited in production."
            )
        if not self.SYNC_DATABASE_URL or not self.SYNC_DATABASE_URL.strip():
            raise ValueError(
                "Production configuration error: Explicit SYNC_DATABASE_URL environment variable is required. "
                "Constructing connection URLs from POSTGRES_* fallback variables is prohibited in production."
            )

        if not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            drv = self.DATABASE_URL.split("://")[0] if "://" in self.DATABASE_URL else "unknown"
            raise ValueError(f"Production configuration error: DATABASE_URL must use 'postgresql+asyncpg' driver (received: '{drv}').")

        if not self.SYNC_DATABASE_URL.startswith("postgresql+psycopg2://"):
            drv = self.SYNC_DATABASE_URL.split("://")[0] if "://" in self.SYNC_DATABASE_URL else "unknown"
            raise ValueError(f"Production configuration error: SYNC_DATABASE_URL must use 'postgresql+psycopg2' driver (received: '{drv}').")

        if is_loopback_host(self.DATABASE_URL):
            raise ValueError("Production configuration error: DATABASE_URL cannot target localhost or a loopback address in production.")

        if is_loopback_host(self.SYNC_DATABASE_URL):
            raise ValueError("Production configuration error: SYNC_DATABASE_URL cannot target localhost or a loopback address in production.")

    @model_validator(mode="after")
    def validate_and_populate_database_urls(self):
        is_prod = self.ENVIRONMENT.lower() in ("production", "prod")

        # Check explicit kwarg or explicit environment variable
        raw_db_url = self.DATABASE_URL if self.DATABASE_URL is not None else os.getenv("DATABASE_URL")
        raw_sync_url = self.SYNC_DATABASE_URL if self.SYNC_DATABASE_URL is not None else os.getenv("SYNC_DATABASE_URL")

        # Phase 2 Local Testing: Explicit Local PostgreSQL isolation toggle (only in non-production)
        if not is_prod and (os.getenv("USE_LOCAL_POSTGRES", "false").lower() in ("true", "1") or os.getenv("TEST_DATABASE_URL")):
            local_url = os.getenv("TEST_DATABASE_URL") or "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_care_companion_test"
            raw_db_url = local_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
            raw_sync_url = local_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

        if is_prod:
            self.DATABASE_URL = raw_db_url.strip() if raw_db_url else ""
            self.SYNC_DATABASE_URL = raw_sync_url.strip() if raw_sync_url else ""
            self.validate_production_database_config()
        else:
            self.DATABASE_URL = raw_db_url.strip() if raw_db_url else f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            self.SYNC_DATABASE_URL = raw_sync_url.strip() if raw_sync_url else f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self

    @property
    def masked_database_url(self) -> str:
        return mask_database_url(self.DATABASE_URL)

    @property
    def masked_sync_database_url(self) -> str:
        return mask_database_url(self.SYNC_DATABASE_URL)

    # Supabase Auth & Storage Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "your-anon-key")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "your-service-role-key")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "super-secret-jwt-key-min-32-chars-long!")
    LOCAL_AUTH_ENABLED: bool = os.getenv("LOCAL_AUTH_ENABLED", "True").lower() == "true"
    
    # Telephony (CallChannel interface with Twilio & Web Channel)
    TELEPHONY_PROVIDER: str = os.getenv("TELEPHONY_PROVIDER", "twilio") # "twilio" or "mock"
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "AC_demo_account_sid")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "demo_auth_token")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "+18005550199")
    TWILIO_WEBHOOK_URL: str = os.getenv("TWILIO_WEBHOOK_URL", "http://localhost:8000/api/v1/telephony/twilio/webhook")

    # Speech & LLM Structured Extraction
    SPEECH_PROVIDER: str = os.getenv("SPEECH_PROVIDER", "sarvam") # "sarvam", "elevenlabs", "mock"
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Clinical Program Constants
    DEFAULT_CALL_WINDOW_START: str = "09:00"
    DEFAULT_CALL_WINDOW_END: str = "19:00"
    DEFAULT_DND_START: str = "21:00"
    DEFAULT_DND_END: str = "08:00"
    MAX_CALL_RETRIES: int = 3
    RETRY_INTERVAL_MINUTES: int = 15
    DEFAULT_MAX_DEFERRALS: int = 2
    DEFERRAL_WINDOW_MINUTES: int = 30
    
    # Alert SLAs in minutes
    ALERT_SLA_CRITICAL_MINUTES: int = 15
    ALERT_SLA_HIGH_MINUTES: int = 60
    ALERT_SLA_MEDIUM_MINUTES: int = 240
    ALERT_SLA_INFO_MINUTES: int = 1440

    # Free-tier Email Service Settings (Resend / Brevo) - Kept Disabled by default
    EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() in ("true", "1")
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "mock")
    RESEND_API_KEY: Optional[str] = os.getenv("RESEND_API_KEY", None)
    BREVO_API_KEY: Optional[str] = os.getenv("BREVO_API_KEY", None)
    EMAIL_FROM_ADDRESS: str = os.getenv("EMAIL_FROM_ADDRESS", "recovery@apexcare.org")

    # Firebase Cloud Messaging (FCM) Web Push - Kept Disabled by default
    FCM_ENABLED: bool = os.getenv("FCM_ENABLED", "false").lower() in ("true", "1")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "ai-care-companion-5df51")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", None)
    
    # Progress Score Weights (PR-01)
    PROGRESS_WEIGHT_MEDICATION: float = 0.40
    PROGRESS_WEIGHT_SYMPTOMS: float = 0.25
    PROGRESS_WEIGHT_HYDRATION: float = 0.15
    PROGRESS_WEIGHT_ACTIVITY: float = 0.20

settings = Settings()
