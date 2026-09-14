"""persist order rejection reason"""

from alembic import op
import sqlalchemy as sa

revision = "0005_order_reason"
down_revision = "0004_execution_outbox_claim"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("reason", sa.String(255), nullable=False, server_default=""))


def downgrade():
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("reason")
