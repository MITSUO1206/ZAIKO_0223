from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_serializer


class DisposalCreate(BaseModel):
    item_id: str
    quantity_disposed: int
    reason: str | None = None
    unit_price_at_disposal: float | None = None
    notes: str | None = None


class DisposalResponse(BaseModel):
    id: str
    item_id: str
    item_code: str
    item_name: str
    quantity_disposed: int
    unit_price_at_disposal: float | None = None
    reason: str | None = None
    disposed_by: str
    ledger_id: str | None = None
    disposed_at: datetime | str
    notes: str | None = None

    @field_serializer("unit_price_at_disposal", when_used="always")
    def _ser_unit_price(self, v: Decimal | float | None) -> float | None:
        if v is None:
            return None
        return float(v)

    @field_serializer("disposed_at", when_used="always")
    def _ser_disposed_at(self, v: datetime | str | None) -> str | None:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)

    class Config:
        from_attributes = True
