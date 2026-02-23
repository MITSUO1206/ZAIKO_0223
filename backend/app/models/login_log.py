"""ログイン成功/失敗履歴（監査用）"""
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class LoginLog(Base):
    __tablename__ = "login_logs"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    login_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
