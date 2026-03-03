"""在庫マスタ API（CRUD + 論理削除 + 監査）"""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models import User, Item
from app.schemas.item_schema import ItemCreate, ItemUpdate, ItemResponse
from app.services.id_service import next_id
from app.services.audit_service import append_audit

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemResponse])
async def list_items(
    q: Annotated[str | None, Query()] = None,
    model_number: Annotated[str | None, Query()] = None,
    current_qty_min: Annotated[int | None, Query()] = None,
    current_qty_max: Annotated[int | None, Query()] = None,
    include_deleted: Annotated[bool, Query()] = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Item)
    if not include_deleted:
        stmt = stmt.where(Item.deleted_at.is_(None))
    if q:
        stmt = stmt.where(or_(
            Item.code.ilike(f"%{q}%"),
            Item.name.ilike(f"%{q}%"),
            Item.model_number.ilike(f"%{q}%"),
        ))
    if model_number:
        stmt = stmt.where(Item.model_number.ilike(f"%{model_number}%"))
    if current_qty_min is not None:
        stmt = stmt.where(Item.current_qty >= current_qty_min)
    if current_qty_max is not None:
        stmt = stmt.where(Item.current_qty <= current_qty_max)
    stmt = stmt.order_by(Item.id)
    r = await db.execute(stmt)
    return list(r.scalars().all())


@router.get("/low-stock", response_model=list[ItemResponse])
async def list_low_stock_items(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """現在庫が安全在庫を下回っている品目一覧（safety_stock > 0 かつ current_qty < safety_stock）"""
    stmt = select(Item).where(
        Item.deleted_at.is_(None),
        Item.safety_stock > 0,
        Item.current_qty < Item.safety_stock,
    ).order_by(Item.current_qty.asc())
    r = await db.execute(stmt)
    return list(r.scalars().all())


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = await db.execute(select(Item).where(Item.id == item_id))
    item = r.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "品目が見つかりません")
    return item


@router.post("", response_model=ItemResponse, status_code=201)
async def create_item(
    body: ItemCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = await db.execute(select(Item).where(Item.code == body.code, Item.deleted_at.is_(None)))
    if r.scalar_one_or_none():
        raise HTTPException(400, "品目コードが重複しています")
    item_id = await next_id(db, "P")
    inbound_date = None
    if body.last_inbound_date:
        try:
            inbound_date = date.fromisoformat(body.last_inbound_date[:10])
        except ValueError:
            pass
    item = Item(
        id=item_id,
        code=body.code,
        name=body.name,
        model_number=body.model_number,
        category=body.category,
        unit=body.unit,
        unit_price=body.unit_price,
        safety_stock=body.safety_stock,
        storage_place=body.storage_place,
        current_qty=0,
        last_lot=body.last_lot,
        last_inbound_qty=body.last_inbound_qty,
        last_inbound_date=inbound_date,
        notes=body.notes,
    )
    db.add(item)
    await append_audit(db, "CREATE", "items", item_id, user.id, before_data=None, after_data=body.model_dump())
    await db.flush()
    await db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: str,
    body: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = await db.execute(select(Item).where(Item.id == item_id, Item.deleted_at.is_(None)))
    item = r.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "品目が見つかりません")
    before = {"code": item.code, "name": item.name, "current_qty": item.current_qty, "model_number": item.model_number, "category": item.category, "unit": item.unit, "unit_price": float(item.unit_price) if item.unit_price else None, "safety_stock": item.safety_stock, "storage_place": item.storage_place, "last_lot": item.last_lot, "last_inbound_qty": item.last_inbound_qty, "last_inbound_date": str(item.last_inbound_date) if item.last_inbound_date else None, "notes": item.notes}
    updates = body.model_dump(exclude_unset=True)
    if "last_inbound_date" in updates:
        s = updates["last_inbound_date"]
        if s is None:
            updates["last_inbound_date"] = None
        elif isinstance(s, str):
            try:
                updates["last_inbound_date"] = date.fromisoformat(s[:10])
            except ValueError:
                updates["last_inbound_date"] = None
    for k in ("code", "name", "model_number", "category", "unit", "unit_price", "safety_stock", "storage_place", "current_qty", "last_lot", "last_inbound_qty", "last_inbound_date", "notes"):
        if k in updates:
            setattr(item, k, updates[k])
    after = {"code": item.code, "name": item.name, "current_qty": item.current_qty, "model_number": item.model_number, "category": item.category, "unit": item.unit, "unit_price": float(item.unit_price) if item.unit_price else None, "safety_stock": item.safety_stock, "storage_place": item.storage_place, "last_lot": item.last_lot, "last_inbound_qty": item.last_inbound_qty, "last_inbound_date": str(item.last_inbound_date) if item.last_inbound_date else None, "notes": item.notes}
    await append_audit(db, "UPDATE", "items", item_id, user.id, before_data=before, after_data=after)
    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_item(
    item_id: str,
    delete_reason: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone
    r = await db.execute(select(Item).where(Item.id == item_id, Item.deleted_at.is_(None)))
    item = r.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "品目が見つかりません")
    before = {"code": item.code, "name": item.name, "current_qty": item.current_qty}
    item.deleted_at = datetime.now(timezone.utc).isoformat()
    item.delete_reason = delete_reason
    await append_audit(db, "DELETE", "items", item_id, user.id, before_data=before, after_data={"delete_reason": delete_reason})
    await db.flush()
    return None
