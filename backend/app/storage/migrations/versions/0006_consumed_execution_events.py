"""add durable consumed execution events

Revision ID: 0006
Revises: 0005
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "consumed_execution_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.String(length=64), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "event_id", name="uq_consumed_execution_events_event_id"
        ),
    )


def downgrade():
    op.drop_table("consumed_execution_events")
