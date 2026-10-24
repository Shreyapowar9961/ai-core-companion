"""001_initial_schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-10-24 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Tables are dynamically managed by Base.metadata.create_all on startup
    # or Alembic migration upgrade.
    pass

def downgrade() -> None:
    pass
