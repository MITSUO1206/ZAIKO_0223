"""ledger_formats, ledger_pages, attachments, notification_*, password_reset_tokens, login_logs

Revision ID: 004
Revises: 003
Create Date: 2025-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ledger_formats",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("input_fields", JSONB, nullable=False),
        sa.Column("has_comment_field", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("pdf_layout", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "ledger_pages",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("format_id", sa.String(20), sa.ForeignKey("ledger_formats.id"), nullable=False),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ledger_pages_format_id", "ledger_pages", ["format_id"])
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("ledger_id", sa.String(20), sa.ForeignKey("ledgers.id"), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("file_type", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_attachments_ledger_id", "attachments", ["ledger_id"])
    op.create_table(
        "notification_settings",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("item_id", sa.String(20), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("safety_stock", sa.Integer(), nullable=False),
        sa.Column("notify_email", sa.String(255), nullable=False),
        sa.Column("suppress_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notification_settings_item_id", "notification_settings", ["item_id"])
    op.create_table(
        "notification_logs",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("item_id", sa.String(20), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("detail", sa.Text(), nullable=True),
    )
    op.create_index("ix_notification_logs_item_id", "notification_logs", ["item_id"])
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(20), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_table(
        "login_logs",
        sa.Column("id", sa.String(20), primary_key=True),
        sa.Column("login_id", sa.String(100), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_login_logs_login_id", "login_logs", ["login_id"])


def downgrade() -> None:
    op.drop_table("login_logs")
    op.drop_table("password_reset_tokens")
    op.drop_table("notification_logs")
    op.drop_table("notification_settings")
    op.drop_table("attachments")
    op.drop_table("ledger_pages")
    op.drop_table("ledger_formats")
