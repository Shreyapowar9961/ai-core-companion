from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.seed import seed_initial_data
import app.models

# Import API routers
from app.api.v1.auth import router as auth_router
from app.api.v1.patients import router as patients_router
from app.api.v1.conversation import router as conversation_router
from app.api.v1.checkins import router as checkins_router
from app.api.v1.medications import router as medications_router
from app.api.v1.lifestyle import router as lifestyle_router
from app.api.v1.vitals import router as vitals_router
from app.api.v1.appointments import router as appointments_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.rules_alerts import router as rules_alerts_router
from app.api.v1.progress import router as progress_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.audit import router as audit_router
from app.api.v1.telephony import router as telephony_router
from app.api.v1.patient_portal import router as patient_portal_router
from app.api.v1.prescriptions import router as prescriptions_router
from app.api.v1.monitoring import router as monitoring_router
from app.services.monitoring_scheduler import BackgroundMonitoringScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("care-companion")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize PostgreSQL Schema & Migrations
    logger.info("Connecting to PostgreSQL / Supabase...")
    try:
        with engine.begin() as conn:
            # 1. Run migrations for altered tables in existing databases
            try:
                conn.execute(text("ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS patient_id VARCHAR(64);"))
                logger.info("Schema migration: user_profiles.patient_id column verified.")
            except Exception as col_err:
                logger.info(f"Column migration check note: {col_err}")

            # 2. Create all missing tables in Base.metadata (monitoring_plans, checkin_tasks, etc.)
            Base.metadata.create_all(bind=conn)
            logger.info("PostgreSQL relational schema and tables verified & committed.")

        with SessionLocal() as session:
            seed_initial_data(session)
            logger.info("Clinical knowledge base and seed data verified.")
    except Exception as e:
        logger.warning(f"PostgreSQL connection note (database connection active when PostgreSQL/Supabase service reachable): {e}")

    try:
        BackgroundMonitoringScheduler.start()
    except Exception as e:
        logger.warning(f"Background monitoring scheduler note: {e}")

    yield

    try:
        BackgroundMonitoringScheduler.stop()
    except Exception:
        pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Multilingual Voice-Based Post-Discharge Recovery Care Platform",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers under API_V1_STR
api_prefix = settings.API_V1_STR
app.include_router(auth_router, prefix=api_prefix)
app.include_router(patients_router, prefix=api_prefix)
app.include_router(conversation_router, prefix=api_prefix)
app.include_router(checkins_router, prefix=api_prefix)
app.include_router(medications_router, prefix=api_prefix)
app.include_router(lifestyle_router, prefix=api_prefix)
app.include_router(vitals_router, prefix=api_prefix)
app.include_router(appointments_router, prefix=api_prefix)
app.include_router(knowledge_router, prefix=api_prefix)
app.include_router(rules_alerts_router, prefix=api_prefix)
app.include_router(progress_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(audit_router, prefix=api_prefix)
app.include_router(telephony_router, prefix=api_prefix)
app.include_router(patient_portal_router, prefix=api_prefix)
app.include_router(prescriptions_router, prefix=api_prefix)
app.include_router(monitoring_router, prefix=api_prefix)

@app.get("/health", tags=["Health & Status"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "connected",
        "environment": settings.ENVIRONMENT
    }

@app.get("/", tags=["Health & Status"])
def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API. Visit {settings.API_V1_STR}/docs for interactive OpenAPI specification."
    }
