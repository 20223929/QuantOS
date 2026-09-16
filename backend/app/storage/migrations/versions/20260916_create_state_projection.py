"""create state projection table.

Revision ID: 20260916_state_projection
Revises:
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260916_state_projection"
down_revision = None
branch_labels = None
depends_on = None



def upgrade() -> None:
    op.create_table(
        "state_projections",
        sa.Column("projection_id", sa.String(length=128), primary_key=True),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_index(
        "ix_state_projections_aggregate_type",
        "state_projections",
        ["aggregate_type"],
    )
    op.create_index(
        "ix_state_projections_aggregate_id",
        "state_projections",
        ["aggregate_id"],
    )



def downgrade() -> None:
    op.drop_index("ix_state_projections_aggregate_id", table_name="state_projections")
    op.drop_index("ix_state_projections_aggregate_type", table_name="state_projections")
    op.drop_table("state_projections")
