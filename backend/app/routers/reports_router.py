"""集計・可視化 API（ダッシュボードKPI・年間在庫推移・廃棄量・安全在庫アラート）"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Item, Ledger, StockTx
from app.models.enums import LedgerType, ApprovalStatus

router = APIRouter(prefix="/reports", tags=["reports"])


def _start_of_month(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


@router.get("/dashboard")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """KPI: 総在庫数・総金額・承認待ち件数・今月入出庫件数・今月廃棄数量/金額"""
    now = datetime.now(timezone.utc)
    month_start = _start_of_month(now)
    # 翌月1日（今月の終わり+1）
    next_month = month_start.month % 12 + 1
    year = month_start.year + (1 if next_month == 1 else 0)
    month_end = month_start.replace(year=year, month=next_month)

    # 総品目数（削除済み除く）
    r = await db.execute(select(func.count(Item.id)).where(Item.deleted_at.is_(None)))
    total_items = r.scalar() or 0

    # 総現在庫数・総在庫金額（削除済み除く）
    r = await db.execute(
        select(
            func.coalesce(func.sum(Item.current_qty), 0).label("qty"),
            func.coalesce(func.sum(Item.current_qty * func.coalesce(Item.unit_price, 0)), 0).label("val"),
        ).where(Item.deleted_at.is_(None))
    )
    row = r.one()
    total_stock_quantity = int(row.qty)
    total_stock_value = float(row.val) if row.val is not None else 0.0

    # 承認待ち件数
    r = await db.execute(select(func.count(Ledger.id)).where(Ledger.status == ApprovalStatus.PENDING))
    pending_count = r.scalar() or 0

    # 今月の帳簿件数（入出庫・払出・廃棄）
    r = await db.execute(
        select(func.count(Ledger.id)).where(
            Ledger.created_at >= month_start,
            Ledger.created_at < month_end,
        )
    )
    this_month_ledgers_count = r.scalar() or 0

    # 今月の廃棄（承認済DISPOSAL、今月作成）
    stmt = select(Ledger, Item.unit_price).join(Item, Ledger.item_id == Item.id).where(
        Ledger.ledger_type == LedgerType.DISPOSAL,
        Ledger.status == ApprovalStatus.APPROVED,
        Ledger.created_at >= month_start,
        Ledger.created_at < month_end,
    )
    r = await db.execute(stmt)
    rows = r.all()
    this_month_disposal_qty = sum(l.quantity for l, _ in rows)
    this_month_disposal_amount = sum(
        l.quantity * (float(up) if up is not None else 0) for l, up in rows
    )

    return {
        "total_items": total_items,
        "total_stock_quantity": total_stock_quantity,
        "total_stock_value": round(total_stock_value, 2),
        "pending_ledgers_count": pending_count,
        "this_month_ledgers_count": this_month_ledgers_count,
        "this_month_disposal_quantity": this_month_disposal_qty,
        "this_month_disposal_amount": round(this_month_disposal_amount, 2),
    }


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
        result.append({
            "ledger_id": l.id,
            "item_id": l.item_id,
            "item_code": item.code if item else "",
            "item_name": item.name if item else "",
            "quantity": l.quantity,
            "unit_price": unit_price,
            "amount": l.quantity * unit_price,
        })
    total_qty = sum(x["quantity"] for x in result)
    total_amount = sum(x["amount"] for x in result)
    return {"year": year, "items": result, "total_quantity": total_qty, "total_amount": total_amount}


@router.get("/safety-stock-alerts")
async def safety_stock_alerts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """安全在庫を下回っている品目一覧（current_qty < safety_stock かつ safety_stock > 0）"""
    stmt = select(Item).where(
        Item.deleted_at.is_(None),
        Item.safety_stock > 0,
        Item.current_qty < Item.safety_stock,
    ).order_by(Item.current_qty.asc())
    r = await db.execute(stmt)
    items = r.scalars().all()
    return {
        "items": [
            {
                "id": i.id,
                "code": i.code,
                "name": i.name,
                "current_qty": i.current_qty,
                "safety_stock": i.safety_stock,
                "unit": i.unit,
            }
            for i in items
        ],
    }
