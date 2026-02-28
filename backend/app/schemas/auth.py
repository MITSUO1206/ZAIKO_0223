"""認証スキーマ"""
from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    login_id: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserMe(BaseModel):
    id: str
    login_id: str
    name: str
    role: str

    model_config = ConfigDict(from_attributes=True)
