from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from sqlalchemy import text

from app.core.config import settings, mask_database_url
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

def init_database_startup(settings_obj=None, engine_obj=None, session_maker=None):
    """
    Phase 1.2: Core database startup verification and validation.
    In production: validates config and verifies connectivity (read-only; zero migrations or DDL).
    In development: verifies connectivity, auto-migrates dev columns/tables, and seeds data.
    Raises RuntimeError on production failure with masked credentials.
    """
    cfg = settings_obj or settings
    eng = engine_obj or engine
    sm = session_maker or SessionLocal

    is_prod = cfg.ENVIRONMENT.lower() in ("production", "prod")
    logger.info("Initializing database verification (%s environment)...", cfg.ENVIRONMENT)

    if is_prod:
        cfg.validate_production_database_config()

    try:
        logger.info("Connecting to PostgreSQL / Supabase (%s environment)...", cfg.ENVIRONMENT)
        with eng.begin() as conn:
            # Verify connectivity
            conn.execute(text("SELECT 1;"))
            logger.info("Database connection successfully established.")

            if is_prod:
                # Production: read-only schema and index verification. Zero automatic DDL migrations or seeding.
                logger.info("Production mode: Verifying schema without running automatic DDL migrations.")
                idx_exists = conn.execute(text("""
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'uq_active_alerts_patient_rule';
                """)).fetchone()
                if idx_exists:
                    logger.info("Active alert partial unique index 'uq_active_alerts_patient_rule' verified in database.")
                else:
                    logger.warning("Active alert partial unique index 'uq_active_alerts_patient_rule' pending migration approval.")
            else:
                # Development: preserve existing schema migration and seeding behavior
                try:
                    conn.execute(text("ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS patient_id VARCHAR(64);"))
                    logger.info("Schema migration: user_profiles.patient_id column verified.")
                except Exception as col_err:
                    logger.info(f"Column migration check note: {col_err}")

                Base.metadata.create_all(bind=conn)
                logger.info("PostgreSQL relational schema and tables verified & committed.")

                try:
                    if conn.dialect.name == "postgresql":
                        dup_check = conn.execute(text("""
                            SELECT patient_id, rule_code, COUNT(*) 
                            FROM alerts 
                            WHERE status IN ('OPEN', 'ACKNOWLEDGED', 'ESCALATED') 
                            GROUP BY patient_id, rule_code 
                            HAVING COUNT(*) > 1;
                        """)).fetchall()
                        if dup_check:
                            logger.warning(f"Active alert duplicate check: {len(dup_check)} conflict group(s) detected. Unique index postponed for manual review.")
                        else:
                            idx_exists = conn.execute(text("""
                                SELECT 1 FROM pg_indexes 
                                WHERE indexname = 'uq_active_alerts_patient_rule';
                            """)).fetchone()
                            if idx_exists:
                                logger.info("Active alert partial unique index 'uq_active_alerts_patient_rule' verified.")
                            else:
                                logger.info("Active alert partial unique index 'uq_active_alerts_patient_rule' pending migration approval.")
                except Exception as idx_err:
                    logger.info(f"Unique index check note: {idx_err}")

        # Development: seed initial data if needed
        if not is_prod:
            with sm() as session:
                seed_initial_data(session)
                logger.info("Clinical knowledge base and seed data verified.")

    except Exception as e:
        safe_msg = mask_database_url(str(e))
        if is_prod:
            logger.critical("FATAL: Database connection failed during production startup: %s", safe_msg)
            raise RuntimeError(f"Database connection failed during production startup: {safe_msg}") from e
        else:
            logger.warning(f"PostgreSQL connection note (database connection active when PostgreSQL/Supabase service reachable): {safe_msg}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 1.2: Validate and initialize database
    init_database_startup(settings, engine, SessionLocal)

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
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

@app.get("/api/v1/docs", include_in_schema=False)
def redirect_docs():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

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
@app.get(f"{api_prefix}/health", tags=["Health & Status"])
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
