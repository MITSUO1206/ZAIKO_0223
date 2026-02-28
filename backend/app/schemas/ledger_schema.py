from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.enums import LedgerType, ApprovalStatus


class LedgerBase(BaseModel):
    item_id: str
    ledger_type: LedgerType
    quantity: int
    lot: str | None = None
    ledger_date: datetime | None = None
    process_name: str | None = None
    notes: str | None = None


class LedgerCreate(LedgerBase):
    pass


class LedgerUpdate(BaseModel):
    item_id: str | None = None
    ledger_type: LedgerType | None = None
    quantity: int | None = None
    lot: str | None = None
    ledger_date: datetime | None = None
    process_name: str | None = None
    notes: str | None = None


class ApproveRejectBody(BaseModel):
    comment: str | None = None


class LedgerResponse(LedgerBase):
    id: str
    status: ApprovalStatus
    created_by: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
