"""廃棄登録 API（廃棄データベースへの登録 + 帳簿 DISPOSAL 作成）"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Item, Ledger, Disposal
from app.models.enums import LedgerType, ApprovalStatus
from app.schemas.disposal_schema import DisposalCreate, DisposalResponse
from app.services.id_service import next_id
from app.services.audit_service import append_audit

router = APIRouter(prefix="/disposals", tags=["disposals"])


def _to_response(d: Disposal) -> DisposalResponse:
    return DisposalResponse(
        id=d.id,
        item_id=d.item_id,
        item_code=d.item_code,
        item_name=d.item_name,
        quantity_disposed=d.quantity_disposed,
        unit_price_at_disposal=float(d.unit_price_at_disposal) if d.unit_price_at_disposal is not None else None,
        reason=d.reason,
        disposed_by=d.disposed_by,
        ledger_id=d.ledger_id,
        disposed_at=d.disposed_at,
        notes=d.notes,
    )


@router.get("", response_model=list[DisposalResponse])
async def list_disposals(
    item_id: Annotated[str | None, Query()] = None,
    q: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query()] = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Disposal).order_by(Disposal.disposed_at.desc()).limit(min(limit, 200))
    if item_id:
        stmt = stmt.where(Disposal.item_id == item_id)
    if q:
        stmt = stmt.where(or_(
            Disposal.item_code.ilike(f"%{q}%"),
            Disposal.item_name.ilike(f"%{q}%"),
            Disposal.reason.ilike(f"%{q}%"),
        ))
    r = await db.execute(stmt)
    return [_to_response(d) for d in r.scalars().all()]


@router.post("", response_model=DisposalResponse, status_code=201)
async def create_disposal(
    body: DisposalCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = await db.execute(select(Item).where(Item.id == body.item_id, Item.deleted_at.is_(None)))
    item = r.scalar_one_or_none()
    if not item:
        raise HTTPException(400, "品目が存在しないか削除済みです")
    if body.quantity_disposed <= 0:
        raise HTTPException(400, "廃棄数量は1以上で指定してください")
    if item.current_qty < body.quantity_disposed:
        raise HTTPException(400, "在庫数量を超える廃棄はできません")

    lid = await next_id(db, "L")
    ledger = Ledger(
        id=lid,
        item_id=body.item_id,
        ledger_type=LedgerType.DISPOSAL,
        quantity=body.quantity_disposed,
        status=ApprovalStatus.PENDING,
        created_by=user.id,
        notes=body.reason or body.notes,
    )
    db.add(ledger)
    await db.flush()

    did = await next_id(db, "D")
    unit_price = body.unit_price_at_disposal if body.unit_price_at_disposal is not None else (float(item.unit_price) if item.unit_price is not None else None)
    disposal = Disposal(
        id=did,
        item_id=body.item_id,
        item_code=item.code,
        item_name=item.name,
        quantity_disposed=body.quantity_disposed,
        unit_price_at_disposal=unit_price,
        reason=body.reason,
        disposed_by=user.id,
        ledger_id=lid,
        notes=body.notes,
    )
    db.add(disposal)
    await append_audit(db, "CREATE", "disposals", did, user.id, before_data=None, after_data=body.model_dump())
    await db.flush()
    await db.refresh(disposal)
    return _to_response(disposal)
