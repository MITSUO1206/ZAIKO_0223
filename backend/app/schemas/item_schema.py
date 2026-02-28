from datetime import date
from pydantic import BaseModel, ConfigDict, field_serializer


class ItemBase(BaseModel):
    code: str
    name: str
    model_number: str | None = None
    category: str | None = None
    unit: str | None = None
    unit_price: float | None = None
    safety_stock: int = 0
    storage_place: str | None = None
    last_lot: str | None = None
    last_inbound_qty: int | None = None
    last_inbound_date: str | None = None  # YYYY-MM-DD
    notes: str | None = None


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    model_number: str | None = None
    category: str | None = None
    unit: str | None = None
    unit_price: float | None = None
    safety_stock: int | None = None
    storage_place: str | None = None
    current_qty: int | None = None
    last_lot: str | None = None
    last_inbound_qty: int | None = None
    last_inbound_date: str | None = None
    notes: str | None = None


class ItemResponse(ItemBase):
    id: str
    current_qty: int = 0
    deleted_at: str | None = None
    delete_reason: str | None = None
    last_inbound_date: date | str | None = None  # ORM は date を返すため

    @field_serializer("last_inbound_date", when_used="always")
    def _ser_date(self, v: date | str | None) -> str | None:
        if v is None:
            return None
        if isinstance(v, date):
            return v.isoformat()
        return str(v)

    model_config = ConfigDict(from_attributes=True)
