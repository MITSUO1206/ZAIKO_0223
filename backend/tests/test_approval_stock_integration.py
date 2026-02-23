"""
統合テスト: 承認 → 在庫反映
- 品目I0001の現在庫から、入庫10の帳簿を承認すると現在庫が+10されることを確認する。
- 実行前に compose up でDB・シード済みであること。
"""
import pytest
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import User, Item, Ledger
from app.models.enums import ApprovalStatus, LedgerType
from app.services.id_service import next_id
from app.services.approval_service import approve_ledger


@pytest.mark.asyncio
async def test_approve_inbound_updates_stock():
    """
    1. 帳簿（入庫10）を1件作成
    2. 承認者でその帳簿を承認
    3. 品目I0001の現在庫が +10 されていることを確認
    """
    async with AsyncSessionLocal() as session:
        # 既存データ確認
        r = await session.execute(select(Item).where(Item.id == "I0001"))
        item_before = r.scalar_one_or_none()
        if not item_before:
            pytest.skip("DBにシードデータがありません。compose up 後にテストDBを用意してください。")
        qty_before = item_before.current_qty

    # 帳簿作成（API経由でなくサービス層で直接作成してから承認する簡易版）
    async with AsyncSessionLocal() as session:
        lid = await next_id(session, "L")
        r = await session.execute(select(User).where(User.login_id == "user"))
        user = r.scalar_one()
        session.add(Ledger(
            id=lid,
            item_id="I0001",
            ledger_type=LedgerType.INBOUND,
            quantity=10,
            status=ApprovalStatus.PENDING,
            created_by=user.id,
        ))
        await session.commit()

    async with AsyncSessionLocal() as session:
        r = await session.execute(select(User).where(User.login_id == "approver"))
        approver = r.scalar_one()
        r2 = await session.execute(select(Ledger).where(Ledger.id == lid))
        ledger = r2.scalar_one()
        await approve_ledger(session, ledger.id, approver)
        await session.commit()

    async with AsyncSessionLocal() as session:
        r = await session.execute(select(Item).where(Item.id == "I0001"))
        item_after = r.scalar_one()
        assert item_after.current_qty == qty_before + 10, "承認後に現在庫が+10されていること"
