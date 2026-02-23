"""disposals テーブル（廃棄データベース）

Revision ID: 006
Revises: 005
Create Date: 2025-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "disposals",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("item_id", sa.String(20), sa.ForeignKey("items.id"), nullable=False, index=True),
        sa.Column("item_code", sa.String(50), nullable=False),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("quantity_disposed", sa.Integer(), nullable=False),
        sa.Column("unit_price_at_disposal", sa.Numeric(12, 2), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("disposed_by", sa.String(20), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("ledger_id", sa.String(20), sa.ForeignKey("ledgers.id"), nullable=True, index=True),
        sa.Column("disposed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("disposals")
