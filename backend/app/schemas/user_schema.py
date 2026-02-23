from pydantic import BaseModel
from app.models.enums import Role


class UserBase(BaseModel):
    login_id: str
    name: str
    role: Role


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: str | None = None
    role: Role | None = None
    password: str | None = None


class UserResponse(UserBase):
    id: str

    class Config:
        from_attributes = True
