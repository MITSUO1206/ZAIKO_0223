from pydantic import BaseModel, ConfigDict


class NotificationSettingBase(BaseModel):
    item_id: str
    safety_stock: int
    notify_email: str
    suppress_hours: int = 24
    is_active: bool = True


class NotificationSettingCreate(NotificationSettingBase):
    pass


class NotificationSettingUpdate(BaseModel):
    safety_stock: int | None = None
    notify_email: str | None = None
    suppress_hours: int | None = None
    is_active: bool | None = None


class NotificationSettingResponse(NotificationSettingBase):
    id: str

    model_config = ConfigDict(from_attributes=True)
