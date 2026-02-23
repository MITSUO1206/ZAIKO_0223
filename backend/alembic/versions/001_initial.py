"""initial tables

Revision ID: 001
Revises:
Create Date: 2025-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "id_sequences",
        sa.Column("prefix", sa.String(4), primary_key=True),
        sa.Column("next_value", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("login_id", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("role", sa.Enum("USER", "APPROVER", "ADMIN", name="role"), nullable=False),
        sa.Column("deleted_at", sa.String(30), nullable=True),
    )
    op.create_index("ix_users_login_id", "users", ["login_id"], unique=True)
    op.create_table(
        "items",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("current_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_items_code", "items", ["code"], unique=True)
    op.create_table(
        "ledgers",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("item_id", sa.String(20), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("ledger_type", sa.Enum("INBOUND", "OUTBOUND", "ISSUE", name="ledgertype"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "APPROVED", "REJECTED", name="approvalstatus"), nullable=False, server_default="PENDING"),
        sa.Column("created_by", sa.String(20), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_ledgers_item_id", "ledgers", ["item_id"])
    op.create_index("ix_ledgers_created_by", "ledgers", ["created_by"])
    op.create_table(
        "stock_tx",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("ledger_id", sa.String(20), sa.ForeignKey("ledgers.id"), nullable=False),
        sa.Column("item_id", sa.String(20), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_stock_tx_ledger_id", "stock_tx", ["ledger_id"])
    op.create_index("ix_stock_tx_item_id", "stock_tx", ["item_id"])
    op.create_table(
        "approval_history",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("ledger_id", sa.String(20), sa.ForeignKey("ledgers.id"), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "APPROVED", "REJECTED", name="approvalstatus"), nullable=False),
        sa.Column("approved_by", sa.String(20), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("signature_hash", sa.String(64), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_approval_history_ledger_id", "approval_history", ["ledger_id"])
    op.create_index("ix_approval_history_approved_by", "approval_history", ["approved_by"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("table_name", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=False),
        sa.Column("before_data", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("after_data", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=True),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_table_name", "audit_logs", ["table_name"])
    op.create_index("ix_audit_logs_target_id", "audit_logs", ["target_id"])
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("approval_history")
    op.drop_table("stock_tx")
    op.drop_table("ledgers")
    op.drop_table("items")
    op.drop_table("users")
    op.drop_table("id_sequences")
    op.execute("DROP TYPE IF EXISTS approvalstatus")
    op.execute("DROP TYPE IF EXISTS ledgertype")
    op.execute("DROP TYPE IF EXISTS role")
