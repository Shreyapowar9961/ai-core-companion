"""003_push_device_registrations

Revision ID: 003_push_device_registrations
Revises: 002_active_alerts_unique_index
Create Date: 2026-11-17 11:30:00.000000

Feature H: Firebase Cloud Messaging (FCM) Web Push Storage
Creates push_device_registrations table for device tokens and notification preferences.
Strictly local preparation — DO NOT apply to production Supabase without approval.
"""
from alembic import op
import sqlalchemy as sa

revision = '003_push_device_registrations'
down_revision = '002_active_alerts_unique_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'push_device_registrations',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('patient_id', sa.String(length=64), sa.ForeignKey('patients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('fcm_token', sa.Text(), nullable=False),
        sa.Column('device_type', sa.String(length=32), server_default='web', nullable=False),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('push_enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_sent_at', sa.DateTime(), nullable=True),
        sa.Column('invalidated_at', sa.DateTime(), nullable=True),
        sa.Column('invalidation_reason', sa.String(length=64), nullable=True),
    )
    op.create_index('ix_push_device_registrations_patient_id', 'push_device_registrations', ['patient_id'])
    op.create_index('ix_push_device_registrations_fcm_token', 'push_device_registrations', ['fcm_token'])
    op.create_index('ix_push_device_registrations_is_active', 'push_device_registrations', ['is_active'])


def downgrade() -> None:
    op.drop_index('ix_push_device_registrations_is_active', table_name='push_device_registrations')
    op.drop_index('ix_push_device_registrations_fcm_token', table_name='push_device_registrations')
    op.drop_index('ix_push_device_registrations_patient_id', table_name='push_device_registrations')
    op.drop_table('push_device_registrations')
