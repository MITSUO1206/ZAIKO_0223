"""帳簿ページ（フォーマットに基づく実体）"""
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class LedgerPage(Base):
    __tablename__ = "ledger_pages"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    format_id: Mapped[str] = mapped_column(ForeignKey("ledger_formats.id"), nullable=False, index=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    format: Mapped["LedgerFormat"] = relationship("LedgerFormat", back_populates="pages")  # noqa: F821
