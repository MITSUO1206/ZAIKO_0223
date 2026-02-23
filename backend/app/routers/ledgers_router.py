"""帳簿 API（CRUD: 未承認のみ編集可、取下げ）"""
from typing import Annotated
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Ledger, Item
from app.models.enums import ApprovalStatus
from app.schemas.ledger_schema import LedgerCreate, LedgerUpdate, LedgerResponse
from app.services.id_service import next_id
from app.services.audit_service import append_audit

router = APIRouter(prefix="/ledgers", tags=["ledgers"])


def _ledger_response(l: Ledger) -> LedgerResponse:
    return LedgerResponse(
        id=l.id,
        item_id=l.item_id,
        ledger_type=l.ledger_type,
        quantity=l.quantity,
        lot=l.lot,
        ledger_date=l.ledger_date,
        process_name=l.process_name,
        status=l.status,
        created_by=l.created_by,
        created_at=l.created_at,
        updated_at=l.updated_at,
        notes=l.notes,
    )


@router.get("", response_model=list[LedgerResponse])
async def list_ledgers(
    q: Annotated[str | None, Query()] = None,
    status: Annotated[ApprovalStatus | None, Query()] = None,
    item_id: Annotated[str | None, Query()] = None,
    process_name: Annotated[str | None, Query()] = None,
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Ledger).where(Ledger.withdrawn_at.is_(None))
    if q:
        stmt = stmt.join(Item, Ledger.item_id == Item.id).where(or_(Item.code.ilike(f"%{q}%"), Item.name.ilike(f"%{q}%")))
    if status is not None:
        stmt = stmt.where(Ledger.status == status)
    if item_id:
        stmt = stmt.where(Ledger.item_id == item_id)
    if process_name:
        stmt = stmt.where(Ledger.process_name.ilike(f"%{process_name}%"))
    if date_from:
        stmt = stmt.where(Ledger.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Ledger.created_at <= date_to)
    stmt = stmt.order_by(Ledger.id.desc())
    r = await db.execute(stmt)
    return [_ledger_response(x) for x in r.scalars().all()]


@router.get("/{ledger_id}", response_model=LedgerResponse)
async def get_ledger(
    ledger_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = await db.execute(select(Ledger).where(Ledger.id == ledger_id))
    ledger = r.scalar_one_or_none()
    if not ledger:
        raise HTTPException(404, "帳簿が見つかりません")
    return _ledger_response(ledger)


@router.post("", response_model=LedgerResponse, status_code=201)
async def create_ledger(
    body: LedgerCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = await db.execute(select(Item).where(Item.id == body.item_id, Item.deleted_at.is_(None)))
    if not r.scalar_one_or_none():
        raise HTTPException(400, "品目が存在しません")
    lid = await next_id(db, "L")
    ledger = Ledger(
        id=lid,
        item_id=body.item_id,
        ledger_type=body.ledger_type,
        quantity=body.quantity,
        lot=body.lot,
        ledger_date=body.ledger_date,
        process_name=body.process_name,
        status=ApprovalStatus.PENDING,
        created_by=user.id,
        notes=body.notes,
    )
    db.add(ledger)
    await append_audit(db, "CREATE", "ledgers", lid, user.id, before_data=None, after_data=body.model_dump())
    await db.flush()
    await db.refresh(ledger)
    return _ledger_response(ledger)


@router.patch("/{ledger_id}", response_model=LedgerResponse)
async def update_ledger(
    ledger_id: str,
    body: LedgerUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = await db.execute(
        select(Ledger).where(Ledger.id == ledger_id, Ledger.status == ApprovalStatus.PENDING, Ledger.withdrawn_at.is_(None))
    )
    ledger = r.scalar_one_or_none()
    if not ledger:
        raise HTTPException(404, "帳簿が見つからないか、未承認のため編集できません")
    before = {"item_id": ledger.item_id, "ledger_type": ledger.ledger_type.value, "quantity": ledger.quantity, "lot": ledger.lot, "ledger_date": str(ledger.ledger_date) if ledger.ledger_date else None, "process_name": ledger.process_name, "notes": ledger.notes}
    updates = body.model_dump(exclude_unset=True)
    for k in ("item_id", "ledger_type", "quantity", "lot", "ledger_date", "process_name", "notes"):
        if k in updates:
            setattr(ledger, k, updates[k])
    after = {"item_id": ledger.item_id, "ledger_type": ledger.ledger_type.value, "quantity": ledger.quantity, "lot": ledger.lot, "ledger_date": str(ledger.ledger_date) if ledger.ledger_date else None, "process_name": ledger.process_name, "notes": ledger.notes}
    await append_audit(db, "UPDATE", "ledgers", ledger_id, user.id, before_data=before, after_data=after)
    await db.flush()
    await db.refresh(ledger)
    return _ledger_response(ledger)


@router.post("/{ledger_id}/withdraw", status_code=204)
async def withdraw_ledger(
    ledger_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = await db.execute(
        select(Ledger).where(Ledger.id == ledger_id, Ledger.status == ApprovalStatus.PENDING, Ledger.withdrawn_at.is_(None))
    )
    ledger = r.scalar_one_or_none()
    if not ledger:
        raise HTTPException(404, "帳簿が見つからないか、取下げできません")
    if ledger.created_by != user.id:
        raise HTTPException(403, "本人のみ取下げできます")
    before = {"status": ledger.status.value}
    ledger.withdrawn_at = datetime.now(timezone.utc).isoformat()
    await append_audit(db, "UPDATE", "ledgers", ledger_id, user.id, before_data=before, after_data={"withdrawn_at": ledger.withdrawn_at})
    await db.flush()
    return None
