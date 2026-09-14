"""add durable execution outbox

Revision ID: 0003_execution_outbox
Revises: 0002_trading_state
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_execution_outbox"
down_revision = "0002_trading_state"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "execution_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("aggregate_id", sa.String(64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("event_id", name="uq_execution_outbox_event_id"),
    )
    op.create_index(
        "ix_execution_outbox_status_id",
        "execution_outbox",
        ["status", "id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_execution_outbox_status_id", table_name="execution_outbox")
    op.drop_table("execution_outbox")
