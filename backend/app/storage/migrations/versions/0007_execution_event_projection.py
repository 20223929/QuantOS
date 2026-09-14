from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "execution_event_projections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("projected_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("event_id", name="uq_execution_event_projections_event_id"),
    )


def downgrade():
    op.drop_table("execution_event_projections")
