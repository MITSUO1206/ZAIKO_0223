"""
main.py で組み立てた app のスモークテスト。
- GET / が期待どおり返る
- /health, /api/health が存在する（main のルート登録の確認）
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_returns_message():
    """GET / は 200 で {"message": "在庫帳簿API"} を返す"""
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"message": "在庫帳簿API"}


def test_health_route_exists():
    """プレフィックスなしの /health が存在する（ローカル用ルート）"""
    try:
        r = client.get("/health")
    except Exception as e:
        # DB が無い（host=db に接続できない）などで例外になる場合はスキップ
        pytest.skip(f"health の実行で例外: {e}")
    assert r.status_code != 404, "ルートが登録されていれば 404 にはならない"


def test_api_health_route_exists():
    """/api/health が存在する（ALB 用ルート）"""
    try:
        r = client.get("/api/health")
    except Exception as e:
        pytest.skip(f"health の実行で例外: {e}")
    assert r.status_code != 404, "ルートが登録されていれば 404 にはならない"
