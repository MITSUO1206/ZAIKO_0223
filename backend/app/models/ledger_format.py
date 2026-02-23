"""帳簿フォーマット（テンプレート）"""
from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class LedgerFormat(Base):
    __tablename__ = "ledger_formats"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    input_fields: Mapped[dict] = mapped_column(JSONB, nullable=False)  # 入力欄定義
    has_comment_field: Mapped[bool] = mapped_column(nullable=False, default=True)
    pdf_layout: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pages: Mapped[list["LedgerPage"]] = relationship("LedgerPage", back_populates="format")
