"""002_active_alerts_unique_index

Revision ID: 002_active_alerts_unique_index
Revises: 001_initial
Create Date: 2026-11-11 11:30:00.000000

Phase 1.1 Correctness Hardening:
Detects existing duplicate active alerts before applying a PostgreSQL
partial unique index on alerts(patient_id, rule_code) WHERE status IN ('OPEN', 'ACKNOWLEDGED', 'ESCALATED').
If duplicates exist, migration is safely halted and offending rows are reported for manual review.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision = '002_active_alerts_unique_index'
down_revision = '001_initial'
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect != 'postgresql':
        return

    # 1. Pre-check for existing duplicate active alerts
    check_query = text("""
        SELECT patient_id, rule_code, COUNT(*) as cnt
        FROM alerts
        WHERE status IN ('OPEN', 'ACKNOWLEDGED', 'ESCALATED')
        GROUP BY patient_id, rule_code
        HAVING COUNT(*) > 1;
    """)
    duplicates = bind.execute(check_query).fetchall()

    if duplicates:
        # Fetch details of affected alerts for manual audit
        detail_query = text("""
            SELECT id, patient_id, rule_code, status, created_at
            FROM alerts
            WHERE status IN ('OPEN', 'ACKNOWLEDGED', 'ESCALATED')
            ORDER BY patient_id, rule_code, created_at;
        """)
        all_active = bind.execute(detail_query).fetchall()
        report = []
        for d in duplicates:
            p_id, r_code, count = d[0], d[1], d[2]
            ids = [row[0] for row in all_active if row[1] == p_id and row[2] == r_code]
            report.append(f"Patient '{p_id}' / Rule '{r_code}': {count} duplicates (Alert IDs: {', '.join(ids)})")
        err_msg = (
            "Cannot apply unique partial index 'uq_active_alerts_patient_rule'. "
            "Pre-existing duplicate active alerts detected in database requiring manual review:\n" +
            "\n".join(report)
        )
        raise RuntimeError(err_msg)

    # 2. Safely apply the PostgreSQL partial unique index
    bind.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_alerts_patient_rule
        ON alerts (patient_id, rule_code)
        WHERE status IN ('OPEN', 'ACKNOWLEDGED', 'ESCALATED');
    """))

def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("DROP INDEX IF EXISTS uq_active_alerts_patient_rule;"))
