"""認証スキーマ"""
from pydantic import BaseModel


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

    class Config:
        from_attributes = True
