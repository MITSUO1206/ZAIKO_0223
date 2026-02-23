"""通知履歴"""
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # popup / email
    sent_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
