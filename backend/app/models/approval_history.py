"""承認履歴（承認/却下時に1件追加、signature_hashで改ざん検知）"""
from sqlalchemy import String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import ApprovalStatus


class ApprovalHistory(Base):
    __tablename__ = "approval_history"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # A0001
    ledger_id: Mapped[str] = mapped_column(ForeignKey("ledgers.id"), nullable=False, index=True)
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), nullable=False)  # APPROVED or REJECTED
    approved_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    signature_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ledger: Mapped["Ledger"] = relationship("Ledger", back_populates="approval_histories")
