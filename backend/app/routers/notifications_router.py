"""発注アラート設定・通知履歴 API"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models import User, NotificationSetting, NotificationLog, Item
from app.models.enums import Role
from app.schemas.notification_schema import NotificationSettingCreate, NotificationSettingUpdate, NotificationSettingResponse
from app.services.id_service import next_id
from app.services.audit_service import append_audit

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/settings", response_model=list[NotificationSettingResponse])
async def list_settings(item_id: Annotated[str | None, Query()] = None, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(NotificationSetting)
    if item_id:
        stmt = stmt.where(NotificationSetting.item_id == item_id)
    r = await db.execute(stmt.order_by(NotificationSetting.id))
    return list(r.scalars().all())


@router.post("/settings", response_model=NotificationSettingResponse, status_code=201)
async def create_setting(body: NotificationSettingCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles(Role.ADMIN))):
    r = await db.execute(select(Item).where(Item.id == body.item_id))
    if not r.scalar_one_or_none():
        raise HTTPException(400, "品目が存在しません")
    nid = await next_id(db, "N")
    ns = NotificationSetting(id=nid, item_id=body.item_id, safety_stock=body.safety_stock, notify_email=body.notify_email, suppress_hours=body.suppress_hours, is_active=body.is_active)
    db.add(ns)
    await append_audit(db, "CREATE", "notification_settings", nid, user.id, before_data=None, after_data=body.model_dump())
    await db.flush()
    await db.refresh(ns)
    return ns


@router.patch("/settings/{setting_id}", response_model=NotificationSettingResponse)
async def update_setting(setting_id: str, body: NotificationSettingUpdate, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles(Role.ADMIN))):
    r = await db.execute(select(NotificationSetting).where(NotificationSetting.id == setting_id))
    ns = r.scalar_one_or_none()
    if not ns:
        raise HTTPException(404, "設定が見つかりません")
    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(ns, k, v)
    await append_audit(db, "UPDATE", "notification_settings", setting_id, user.id, before_data=None, after_data=updates)
    await db.flush()
    await db.refresh(ns)
    return ns


@router.get("/alerts/check")
async def check_alerts(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """安全在庫を下回っている品目一覧（アラート判定）"""
    r = await db.execute(select(Item, NotificationSetting).join(NotificationSetting, Item.id == NotificationSetting.item_id).where(NotificationSetting.is_active == True, Item.deleted_at.is_(None)))
    rows = r.all()
    below = []
    for item, ns in rows:
        if item.current_qty < ns.safety_stock:
            below.append({"item_id": item.id, "code": item.code, "name": item.name, "current_qty": item.current_qty, "safety_stock": ns.safety_stock, "notify_email": ns.notify_email})
    return {"items_below_safety_stock": below}
