"""廃棄データベース（廃棄削除した品目・数量・単価を記録）"""
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Disposal(Base):
    __tablename__ = "disposals"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # D0001
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    item_code: Mapped[str] = mapped_column(String(50), nullable=False)  # 廃棄時点の品目コード（参照用）
    item_name: Mapped[str] = mapped_column(String(200), nullable=False)  # 廃棄時点の品目名（参照用）
    quantity_disposed: Mapped[int] = mapped_column(Integer, nullable=False)  # 廃棄数量
    unit_price_at_disposal: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)  # 廃棄時単価
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)  # 廃棄理由
    disposed_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    ledger_id: Mapped[str | None] = mapped_column(ForeignKey("ledgers.id"), nullable=True, index=True)  # 紐づく帳簿
    disposed_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    item: Mapped["Item"] = relationship("Item", back_populates="disposals")
