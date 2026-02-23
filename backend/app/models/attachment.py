"""帳簿添付ファイル（PDF等）"""
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    ledger_id: Mapped[str] = mapped_column(ForeignKey("ledgers.id"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)  # 保存先パスまたはS3キー
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 種別
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
