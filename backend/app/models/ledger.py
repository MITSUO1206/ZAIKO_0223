"""帳簿トランザクション"""
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import LedgerType, ApprovalStatus


class Ledger(Base):
    __tablename__ = "ledgers"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # L0001
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    ledger_type: Mapped[LedgerType] = mapped_column(Enum(LedgerType), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    lot: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)  # ロット
    ledger_date: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)  # 日付（既定=登録日）
    process_name: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 工程名（払い出し時）
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    withdrawn_at: Mapped[str | None] = mapped_column(String(30), nullable=True)

    item: Mapped["Item"] = relationship("Item", back_populates="ledgers")
    created_by_user: Mapped["User"] = relationship("User", back_populates="ledgers", foreign_keys=[created_by])
    approval_histories: Mapped[list["ApprovalHistory"]] = relationship("ApprovalHistory", back_populates="ledger")
    stock_txs: Mapped[list["StockTx"]] = relationship("StockTx", back_populates="ledger")
