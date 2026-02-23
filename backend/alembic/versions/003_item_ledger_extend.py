"""item/ledger columns extend + DISPOSAL

Revision ID: 003
Revises: 002
Create Date: 2025-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("items", sa.Column("model_number", sa.String(100), nullable=True))
    op.add_column("items", sa.Column("category", sa.String(100), nullable=True))
    op.add_column("items", sa.Column("unit", sa.String(20), nullable=True))
    op.add_column("items", sa.Column("unit_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("items", sa.Column("safety_stock", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("items", sa.Column("storage_place", sa.String(100), nullable=True))
    op.add_column("items", sa.Column("delete_reason", sa.Text(), nullable=True))
    op.create_index("ix_items_model_number", "items", ["model_number"], unique=False)

    op.execute("""
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid WHERE t.typname = 'ledgertype' AND e.enumlabel = 'DISPOSAL') THEN
    ALTER TYPE ledgertype ADD VALUE 'DISPOSAL';
  END IF;
END $$;
""")
    op.add_column("ledgers", sa.Column("lot", sa.String(100), nullable=True))
    op.add_column("ledgers", sa.Column("ledger_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ledgers", sa.Column("process_name", sa.String(100), nullable=True))
    op.create_index("ix_ledgers_lot", "ledgers", ["lot"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ledgers_lot", table_name="ledgers")
    op.drop_column("ledgers", "process_name")
    op.drop_column("ledgers", "ledger_date")
    op.drop_column("ledgers", "lot")
    op.drop_index("ix_items_model_number", table_name="items")
    op.drop_column("items", "delete_reason")
    op.drop_column("items", "storage_place")
    op.drop_column("items", "safety_stock")
    op.drop_column("items", "unit_price")
    op.drop_column("items", "unit")
    op.drop_column("items", "category")
    op.drop_column("items", "model_number")
