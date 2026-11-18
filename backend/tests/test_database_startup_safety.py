"""
Phase 1.2: Production Database Startup Safety Tests.
Validates:
1. Production requires explicit DATABASE_URL.
2. Production requires explicit SYNC_DATABASE_URL.
3. Production rejects localhost or loopback fallback.
4. Production rejects non-PostgreSQL drivers (must be postgresql+asyncpg and postgresql+psycopg2).
5. Production accepts valid Supabase PostgreSQL URL formats.
6. Production database connection failure raises RuntimeError, failing fast without exposing credentials.
7. Development mode remains compatible with local defaults and non-fatal connection notes.
8. Credentials, passwords, and tokens are never exposed in error logs or string outputs.

Strictly PostgreSQL test suite. Zero SQLite. Zero connection to Supabase production.
"""
import pytest
from sqlalchemy.exc import OperationalError
from app.core.config import Settings, mask_database_url, is_loopback_host
from app.main import init_database_startup


def test_production_only_postgres_variables_fails(monkeypatch):
    """
    Requirement: Production with only POSTGRES_* fallback variables fails.
    Constructing connection URLs from POSTGRES_* fallback variables is prohibited in production.
    """
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("POSTGRES_SERVER", "aws-0-ap-south-1.pooler.supabase.com")
    monkeypatch.setenv("POSTGRES_USER", "postgres.ref")
    monkeypatch.setenv("POSTGRES_PASSWORD", "some_secret_pass")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SYNC_DATABASE_URL", raising=False)

    with pytest.raises((ValueError, Exception)) as exc_info:
        Settings()
    assert "Explicit DATABASE_URL" in str(exc_info.value)
    assert "Constructing connection URLs from POSTGRES_* fallback variables is prohibited" in str(exc_info.value)


def test_production_missing_database_url():
    """
    Requirement 1: In production, require explicit DATABASE_URL.
    """
    with pytest.raises((ValueError, Exception)) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="",
            SYNC_DATABASE_URL="postgresql+psycopg2://postgres.ref:secret@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
        )
    assert "Explicit DATABASE_URL" in str(exc_info.value)


def test_production_missing_sync_database_url():
    """
    Requirement 2: In production, require explicit SYNC_DATABASE_URL.
    """
    with pytest.raises((ValueError, Exception)) as exc_info:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://postgres.ref:secret@aws-0-ap-south-1.pooler.supabase.com:6543/postgres",
            SYNC_DATABASE_URL=""
        )
    assert "Explicit SYNC_DATABASE_URL" in str(exc_info.value)


def test_production_localhost_fallback_rejected():
    """
    Requirement 3: Do not allow production to silently fall back to localhost.
    """
    # Test localhost in DATABASE_URL
    with pytest.raises((ValueError, Exception)) as exc1:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://postgres:secret@localhost:5432/ai_care_companion",
            SYNC_DATABASE_URL="postgresql+psycopg2://postgres.ref:secret@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
        )
    assert "localhost or a loopback address" in str(exc1.value)

    # Test 127.0.0.1 in SYNC_DATABASE_URL
    with pytest.raises((ValueError, Exception)) as exc2:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://postgres.ref:secret@aws-0-ap-south-1.pooler.supabase.com:6543/postgres",
            SYNC_DATABASE_URL="postgresql+psycopg2://postgres:secret@127.0.0.1:5432/ai_care_companion"
        )
    assert "localhost or a loopback address" in str(exc2.value)

    # Test ::1 (IPv6 loopback)
    assert is_loopback_host("postgresql+asyncpg://postgres:secret@[::1]:5432/db") is True


def test_production_invalid_database_driver():
    """
    Requirement 4: Validate that both URLs use PostgreSQL-compatible drivers.
    """
    # Wrong driver on async URL
    with pytest.raises((ValueError, Exception)) as exc1:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+psycopg2://postgres.ref:secret@aws-0.supabase.com:6543/postgres",
            SYNC_DATABASE_URL="postgresql+psycopg2://postgres.ref:secret@aws-0.supabase.com:6543/postgres"
        )
    assert "postgresql+asyncpg" in str(exc1.value)

    # Wrong driver on sync URL
    with pytest.raises((ValueError, Exception)) as exc2:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://postgres.ref:secret@aws-0.supabase.com:6543/postgres",
            SYNC_DATABASE_URL="postgresql+asyncpg://postgres.ref:secret@aws-0.supabase.com:6543/postgres"
        )
    assert "postgresql+psycopg2" in str(exc2.value)

    # Non-PostgreSQL driver
    with pytest.raises((ValueError, Exception)) as exc3:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="mysql+pymysql://user:pass@aws-0.supabase.com:3306/db",
            SYNC_DATABASE_URL="postgresql+psycopg2://postgres.ref:secret@aws-0.supabase.com:6543/postgres"
        )
    assert "postgresql+asyncpg" in str(exc3.value)


def test_production_valid_supabase_url_format():
    """
    Requirement 5: Production with valid Supabase PostgreSQL URL format succeeds.
    """
    s = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql+asyncpg://postgres.testref:my_secure_pw@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require",
        SYNC_DATABASE_URL="postgresql+psycopg2://postgres.testref:my_secure_pw@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
    )
    assert s.ENVIRONMENT == "production"
    assert s.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert s.SYNC_DATABASE_URL.startswith("postgresql+psycopg2://")
    assert "aws-0-ap-south-1.pooler.supabase.com" in s.DATABASE_URL


def test_production_database_connection_failure_raises():
    """
    Requirement 6: In production, database connection failure raises and prevents app startup.
    Ensures credentials/passwords are never exposed in log outputs or exception messages.
    """
    secret_pass = "UltraSecretProdPass!999"
    test_settings = Settings(
        ENVIRONMENT="production",
        DATABASE_URL=f"postgresql+asyncpg://postgres.testref:{secret_pass}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require",
        SYNC_DATABASE_URL=f"postgresql+psycopg2://postgres.testref:{secret_pass}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
    )

    class FailingEngine:
        def begin(self):
            raise OperationalError(
                f"connection to server failed: password={secret_pass} auth failed",
                params=None,
                orig=None
            )

    with pytest.raises(RuntimeError) as exc_info:
        init_database_startup(settings_obj=test_settings, engine_obj=FailingEngine())

    assert "Database connection failed during production startup" in str(exc_info.value)
    # Ensure password is not exposed in the exception message
    assert secret_pass not in str(exc_info.value)


def test_development_mode_behavior_remains_compatible():
    """
    Requirement 7: Development mode remains compatible with local defaults.
    """
    s = Settings(
        ENVIRONMENT="development",
        DATABASE_URL="",
        SYNC_DATABASE_URL="",
        POSTGRES_SERVER="localhost"
    )
    assert s.ENVIRONMENT == "development"
    assert "localhost" in s.DATABASE_URL
    assert s.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert s.SYNC_DATABASE_URL.startswith("postgresql+psycopg2://")


def test_development_startup_tolerates_offline_db():
    """
    Requirement 7 (cont.): In development, database failure logs a warning without raising RuntimeError.
    """
    dev_settings = Settings(
        ENVIRONMENT="development",
        DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_care_companion",
        SYNC_DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/ai_care_companion"
    )

    class FailingEngine:
        def begin(self):
            raise OperationalError("connection to server failed", params=None, orig=None)

    # Lifespan/startup should log warning and not raise in development
    init_database_startup(settings_obj=dev_settings, engine_obj=FailingEngine())


def test_passwords_not_exposed_in_logs_and_errors():
    """
    Requirement 8: Passwords and tokens are never exposed in logs or masked URLs.
    """
    secret = "SuperSecretPassword123!"
    raw_url = f"postgresql+asyncpg://postgres.projectref:{secret}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
    masked = mask_database_url(raw_url)
    assert secret not in masked
    assert "postgres.projectref:***@" in masked

    # Error message masking
    raw_err = f"OperationalError: password={secret} auth failed for user postgres"
    masked_err = mask_database_url(raw_err)
    assert secret not in masked_err
    assert "password=***" in masked_err
