"""集計・可視化 API（年間在庫推移・廃棄量）"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Item, Ledger, StockTx
from app.models.enums import LedgerType, ApprovalStatus

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/stock-transition")
async def stock_transition(
    item_id: Annotated[str | None, Query()] = None,
    year: Annotated[int, Query()] = 2025,
    granularity: Annotated[str, Query()] = "month",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """商品ごとの在庫推移（月別/週別集計）。stock_tx と created_at で集計。"""
    # 簡易実装: その年の stock_tx を item_id ごとに集計
    stmt = select(StockTx.item_id, func.sum(StockTx.quantity_delta).label("delta"), func.date_trunc("month", StockTx.created_at).label("period")).where(func.extract("year", StockTx.created_at) == year)
    if item_id:
        stmt = stmt.where(StockTx.item_id == item_id)
    stmt = stmt.group_by(StockTx.item_id, func.date_trunc("month", StockTx.created_at))
    r = await db.execute(stmt)
    rows = r.all()
    by_item = {}
    for row in rows:
        key = row.item_id
        if key not in by_item:
            by_item[key] = []
        by_item[key].append({"period": str(row.period)[:7], "delta": row.delta})
    return {"year": year, "granularity": granularity, "data": by_item}


@router.get("/disposal")
async def disposal_report(
    item_id: Annotated[str | None, Query()] = None,
    year: Annotated[int, Query()] = 2025,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """廃棄量・金額（帳簿種別=DISPOSAL）。単価は品目マスタの現行単価で計算。"""
    stmt = select(Ledger).where(Ledger.ledger_type == LedgerType.DISPOSAL, Ledger.status == ApprovalStatus.APPROVED, func.extract("year", Ledger.created_at) == year)
    if item_id:
        stmt = stmt.where(Ledger.item_id == item_id)
    r = await db.execute(stmt)
    ledgers = r.scalars().all()
    result = []
    for l in ledgers:
        r2 = await db.execute(select(Item).where(Item.id == l.item_id))
        item = r2.scalar_one_or_none()
        unit_price = float(item.unit_price) if item and item.unit_price else 0
        result.append({"ledger_id": l.id, "item_id": l.item_id, "quantity": l.quantity, "unit_price": unit_price, "amount": l.quantity * unit_price})
    total_qty = sum(x["quantity"] for x in result)
    total_amount = sum(x["amount"] for x in result)
    return {"year": year, "items": result, "total_quantity": total_qty, "total_amount": total_amount}
