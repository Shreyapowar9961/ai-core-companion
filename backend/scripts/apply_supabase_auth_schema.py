import sys
import os
sys.path.insert(0, os.path.abspath("backend"))

import psycopg2
from app.core.config import settings
from app.core.security import hash_password

def apply_schema():
    conn_str = os.getenv("SYNC_DATABASE_URL") or settings.SYNC_DATABASE_URL
    if "postgresql+psycopg2://" in conn_str:
        conn_str = conn_str.replace("postgresql+psycopg2://", "postgresql://")

    print("Connecting to live Supabase PostgreSQL database...")
    conn = psycopg2.connect(conn_str)
    conn.autocommit = True
    cur = conn.cursor()

    print("1. Creating user_profiles and revoked_tokens tables...")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        id VARCHAR(64) PRIMARY KEY,
        email VARCHAR(128) UNIQUE NOT NULL,
        full_name VARCHAR(128) NOT NULL,
        role VARCHAR(32) NOT NULL DEFAULT 'CLINICIAN',
        facility_id VARCHAR(64) REFERENCES facilities(id) ON DELETE SET NULL,
        password_hash VARCHAR(255),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);
    CREATE INDEX IF NOT EXISTS idx_user_profiles_facility ON user_profiles(facility_id);

    CREATE TABLE IF NOT EXISTS revoked_tokens (
        token_sig VARCHAR(128) PRIMARY KEY,
        user_id VARCHAR(64),
        revoked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP WITH TIME ZONE
    );
    """)

    print("2. Ensuring facilities exist...")
    cur.execute("""
    INSERT INTO facilities (id, name, code, contact_phone, created_at)
    VALUES 
    ('facility-apex-1', 'Apex Heart & Recovery Institute', 'APEX', '+9118005550199', NOW()),
    ('facility-metropolis-2', 'Metropolis Specialty Hospital', 'METRO', '+912233445566', NOW())
    ON CONFLICT (id) DO NOTHING;
    """)

    print("3. Generating PBKDF2 password hashes...")
    neha_hash = hash_password("Clinician123!")
    admin_hash = hash_password("Admin123!")
    patil_hash = hash_password("Clinician123!")

    print("4. Upserting authorized staff profiles...")
    cur.execute("""
    INSERT INTO user_profiles (id, email, full_name, role, facility_id, password_hash, is_active)
    VALUES 
    ('user-neha-101', 'dr.neha@apexcare.org', 'Dr. Neha Kulkarni', 'CLINICIAN', 'facility-apex-1', %s, TRUE),
    ('user-admin-1', 'admin@apexcare.org', 'Rajesh Sharma (Admin)', 'ADMIN', 'facility-apex-1', %s, TRUE),
    ('user-patil-202', 'dr.patil@metropolis.org', 'Dr. Ramesh Patil', 'CLINICIAN', 'facility-metropolis-2', %s, TRUE)
    ON CONFLICT (email) DO UPDATE SET
        password_hash = EXCLUDED.password_hash,
        role = EXCLUDED.role,
        facility_id = EXCLUDED.facility_id,
        full_name = EXCLUDED.full_name;
    """, (neha_hash, admin_hash, patil_hash))

    print("5. Enabling Row Level Security (RLS)...")
    cur.execute("""
    ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
    ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
    ALTER TABLE vital_readings ENABLE ROW LEVEL SECURITY;
    ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
    """)

    print("6. Verifying live user_profiles...")
    cur.execute("SELECT id, email, full_name, role, facility_id, is_active FROM user_profiles;")
    rows = cur.fetchall()
    for row in rows:
        print(f"   [SUCCESS] {row[1]} | {row[2]} | Role: {row[3]} | Facility: {row[4]} | Active: {row[5]}")

    cur.close()
    conn.close()
    print("Database schema & seed users successfully applied to Supabase!")

if __name__ == "__main__":
    apply_schema()
