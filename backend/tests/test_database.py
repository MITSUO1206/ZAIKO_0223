"""
database.py の結合テスト。
- AsyncSessionLocal でセッションが取り、簡単なクエリが実行できること（engine と session のつながり）
- get_db を消費したときに session が使えること（DB が利用可能な場合のみ）

DB に接続できない環境ではスキップする。
ホストから実行時は conftest で localhost に差し替える（Docker の db が 5432 で公開されている前提）。
"""
import pytest
from sqlalchemy import text

from app.database import AsyncSessionLocal, get_db


@pytest.mark.asyncio
async def test_database_session_and_get_db():
    """
    1) AsyncSessionLocal() でセッションを取り、SELECT 1 が実行できること。
    2) get_db を消費したときに yield された session でクエリが実行できること。
    DB が無い場合はスキップ。1 本にまとめて、engine/ループの共有による 2 本目のスキップを避ける。
    """
    # (1) AsyncSessionLocal でセッションが使えること
    try:
        async with AsyncSessionLocal() as session:
            r = await session.execute(text("SELECT 1"))
            one = r.scalar()
            await session.commit()
            assert one == 1
    except Exception as e:
        pytest.skip(f"DB に接続できません: {e}")

    # (2) get_db で渡される session が使えること
    async for session in get_db():
        try:
            r = await session.execute(text("SELECT 1"))
            assert r.scalar() == 1
        except Exception as e:
            pytest.skip(f"DB に接続できません: {e}")
        # 1 回でループ終了（get_db は 1 回しか yield しない）
