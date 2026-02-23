"""利用者マスタ"""
from sqlalchemy import String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import Role


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # U0001
    login_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    deleted_at: Mapped[str | None] = mapped_column(String(30), nullable=True)  # 論理削除

    ledgers: Mapped[list["Ledger"]] = relationship("Ledger", back_populates="created_by_user", foreign_keys="Ledger.created_by")
