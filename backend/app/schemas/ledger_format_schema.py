from pydantic import BaseModel
from typing import Any


class LedgerFormatBase(BaseModel):
    name: str
    version: int = 1
    input_fields: dict[str, Any]
    has_comment_field: bool = True
    pdf_layout: dict[str, Any] | None = None


class LedgerFormatCreate(LedgerFormatBase):
    pass


class LedgerFormatResponse(LedgerFormatBase):
    id: str

    class Config:
        from_attributes = True


class LedgerPageCreate(BaseModel):
    format_id: str
    memo: str | None = None


class LedgerPageResponse(BaseModel):
    id: str
    format_id: str
    memo: str | None = None

    class Config:
        from_attributes = True
