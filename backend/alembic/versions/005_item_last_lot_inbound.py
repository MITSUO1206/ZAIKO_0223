"""items: last_lot, last_inbound_qty, last_inbound_date

Revision ID: 005
Revises: 004
Create Date: 2025-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("items", sa.Column("last_lot", sa.String(100), nullable=True))
    op.add_column("items", sa.Column("last_inbound_qty", sa.Integer(), nullable=True))
    op.add_column("items", sa.Column("last_inbound_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "last_inbound_date")
    op.drop_column("items", "last_inbound_qty")
    op.drop_column("items", "last_lot")
