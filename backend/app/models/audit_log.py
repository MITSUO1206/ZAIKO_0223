"""監査ログ（before/after + ハッシュチェーン）"""
from sqlalchemy import String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # G0001 (audit)
    action: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # CREATE/UPDATE/DELETE/APPROVE
    table_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    before_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
