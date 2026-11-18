import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.core.database import Base
import app.models  # Ensure all models are registered

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_target_url() -> str:
    url = os.getenv('ALEMBIC_DATABASE_URL') or os.getenv('TEST_DATABASE_URL') or settings.SYNC_DATABASE_URL
    if not url:
        url = 'postgresql+psycopg2://postgres:postgres@localhost:5432/ai_care_companion_test'

    # Strict safety block: prevent accidental migration on production Supabase
    is_supabase = 'supabase' in url.lower() or 'aws-0-ap-south-1' in url.lower()
    if is_supabase and os.getenv('ALLOW_PRODUCTION_MIGRATIONS', 'false').lower() != 'true':
        raise RuntimeError(
            'CRITICAL SAFETY BLOCK: Alembic migration is targeting Supabase production! '
            'To prevent unintended schema changes to production, set ALLOW_PRODUCTION_MIGRATIONS=true explicitly.'
        )
    return url


def run_migrations_offline() -> None:
    url = get_target_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_target_url()
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = url
    connectable = engine_from_config(
        configuration,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
