"""在庫トランザクション（承認時にのみ追加）"""
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class StockTx(Base):
    __tablename__ = "stock_tx"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # S0001
    ledger_id: Mapped[str] = mapped_column(ForeignKey("ledgers.id"), nullable=False, index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)  # +入庫 / -出庫・払出
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ledger: Mapped["Ledger"] = relationship("Ledger", back_populates="stock_txs")
    item: Mapped["Item"] = relationship("Item", back_populates="stock_txs")
