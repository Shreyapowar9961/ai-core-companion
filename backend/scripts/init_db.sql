-- PostgreSQL & Supabase Database Initialization
-- AI Care Companion Relational Architecture

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Initial schema tables are created and managed by Alembic / SQLAlchemy ORM
-- Default privileges
GRANT ALL PRIVILEGES ON DATABASE ai_care_companion TO postgres;
