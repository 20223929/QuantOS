"""expand trading state persistence

Revision ID: 0002_trading_state
Revises: 0001_initial_schema
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_trading_state"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("order_id", sa.String(64), nullable=True))
    op.add_column("orders", sa.Column("volume", sa.Float(), nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("price", sa.Float(), nullable=True))
    op.add_column("orders", sa.Column("offset", sa.String(16), nullable=False, server_default="OPEN"))
    op.create_index("ix_orders_order_id", "orders", ["order_id"], unique=True)

    op.add_column("trades", sa.Column("trade_id", sa.String(64), nullable=True))
    op.add_column("trades", sa.Column("side", sa.String(16), nullable=False, server_default="BUY"))
    op.create_index("ix_trades_trade_id", "trades", ["trade_id"], unique=True)

    op.create_index("ix_positions_symbol_unique", "positions", ["symbol"], unique=True)


def downgrade():
    op.drop_index("ix_positions_symbol_unique", table_name="positions")
    op.drop_index("ix_trades_trade_id", table_name="trades")
    op.drop_column("trades", "side")
    op.drop_column("trades", "trade_id")
    op.drop_index("ix_orders_order_id", table_name="orders")
    op.drop_column("orders", "offset")
    op.drop_column("orders", "price")
    op.drop_column("orders", "volume")
    op.drop_column("orders", "order_id")
