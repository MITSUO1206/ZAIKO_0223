"""アプリ設定（環境変数から読み込み）"""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# プロジェクトルートの .env を必ず参照（backend から実行しても同じファイルを読む）
_CONFIG_DIR = Path(__file__).resolve().parent  # backend/app
_PROJECT_ROOT = _CONFIG_DIR.parent.parent  # 在庫管理アプリ
_ENV_FILE = _PROJECT_ROOT / ".env"


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

    # CORS（カンマ区切りで複数可。未設定時は localhost のみ）
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [s.strip() for s in self.cors_origins.split(",") if s.strip()]

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )


settings = Settings()
