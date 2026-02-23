"""在庫マスタ（品目）"""
from sqlalchemy import String, Integer, Numeric, DateTime, Date, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # I0001
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)  # 型番
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 単位
    unit_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)  # 単価
    safety_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 安全在庫
    storage_place: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 保管場所
    current_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_lot: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 直近LOT
    last_inbound_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 直近入庫数
    last_inbound_date: Mapped[str | None] = mapped_column(Date, nullable=True)  # 直近入庫日
    deleted_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    delete_reason: Mapped[str | None] = mapped_column(Text, nullable=True)  # 削除理由
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    ledgers: Mapped[list["Ledger"]] = relationship("Ledger", back_populates="item")
    stock_txs: Mapped[list["StockTx"]] = relationship("StockTx", back_populates="item")
    disposals: Mapped[list["Disposal"]] = relationship("Disposal", back_populates="item")
