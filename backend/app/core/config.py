import os
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

class Settings(BaseModel):
    PROJECT_NAME: str = "AI Care Companion"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Host
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ]
    
    # Database: Strictly PostgreSQL and Supabase
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "ai_care_companion")

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"postgresql+asyncpg://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_SERVER', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'ai_care_companion')}"
    )
    SYNC_DATABASE_URL: str = os.getenv(
        "SYNC_DATABASE_URL", 
        f"postgresql+psycopg2://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_SERVER', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'ai_care_companion')}"
    )

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
    
    # Progress Score Weights (PR-01)
    PROGRESS_WEIGHT_MEDICATION: float = 0.40
    PROGRESS_WEIGHT_SYMPTOMS: float = 0.25
    PROGRESS_WEIGHT_HYDRATION: float = 0.15
    PROGRESS_WEIGHT_ACTIVITY: float = 0.20

settings = Settings()
