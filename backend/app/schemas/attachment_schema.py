from pydantic import BaseModel, ConfigDict


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

    model_config = ConfigDict(from_attributes=True)
