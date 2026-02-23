"""ID採番用シーケンス（prefix毎に連番、SELECT FOR UPDATEで安全採番）"""
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IdSequence(Base):
    __tablename__ = "id_sequences"

    prefix: Mapped[str] = mapped_column(String(4), primary_key=True)  # U, I, L, S, A, G
    next_value: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
