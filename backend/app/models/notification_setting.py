"""発注アラート設定"""
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    safety_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    notify_email: Mapped[str] = mapped_column(String(255), nullable=False)
    suppress_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)  # 抑止期間(時間)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
