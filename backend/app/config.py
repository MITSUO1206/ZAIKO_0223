"""アプリ設定（環境変数から読み込み）"""
from pydantic import field_validator
from pydantic_settings import BaseSettings


def _normalize_api_key(v: str | None) -> str:
    """API キーを正規化: BOM/CRLF/改行・前後の引用符や空白を除去"""
    if v is None:
        return ""
    s = (v or "").replace("\ufeff", "").replace("\r", "").replace("\n", "").strip()
    if len(s) >= 2 and (s[0] == s[-1] == '"' or s[0] == s[-1] == "'"):
        s = s[1:-1].strip()
    return s


class Settings(BaseSettings):
    """設定"""

    # DB
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/inventory"
    database_url_sync: str = "postgresql://postgres:postgres@db:5432/inventory"

    # Gemini（チャット照会 LLM）
    gemini_api_key: str = ""

    @field_validator("gemini_api_key", mode="after")
    @classmethod
    def strip_gemini_key(cls, v: str) -> str:
        return _normalize_api_key(v)

    # JWT
    secret_key: str = "change-me-in-production-use-env"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8-sig"  # Windows で .env に BOM が付いても正しく読む
        extra = "ignore"


settings = Settings()
