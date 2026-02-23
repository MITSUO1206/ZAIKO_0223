"""パスワード再設定用ワンタイムトークン"""
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # トークンそのもの
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    expires_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
