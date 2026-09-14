"""add execution outbox claim ownership

Revision ID: 0004_execution_outbox_claim
Revises: 0003_execution_outbox
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_execution_outbox_claim"
down_revision = "0003_execution_outbox"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("execution_outbox", sa.Column("claim_owner", sa.String(128), nullable=True))
    op.add_column("execution_outbox", sa.Column("claim_expires_at", sa.DateTime(), nullable=True))
    op.create_index(
        "ix_execution_outbox_claim",
        "execution_outbox",
        ["status", "claim_expires_at", "id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_execution_outbox_claim", table_name="execution_outbox")
    op.drop_column("execution_outbox", "claim_expires_at")
    op.drop_column("execution_outbox", "claim_owner")
