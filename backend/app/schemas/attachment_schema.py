from pydantic import BaseModel


class AttachmentCreate(BaseModel):
    ledger_id: str
    title: str | None = None
    file_type: str | None = None


class AttachmentResponse(BaseModel):
    id: str
    ledger_id: str
    file_path: str
    title: str | None = None
    file_type: str | None = None

    class Config:
        from_attributes = True
