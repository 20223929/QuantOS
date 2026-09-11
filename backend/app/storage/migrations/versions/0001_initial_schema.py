"""initial schema migration

Revision ID: 0001_initial_schema
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "market_data",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table("market_data")
    op.drop_table("positions")
    op.drop_table("trades")
    op.drop_table("orders")
