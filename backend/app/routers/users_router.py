"""利用者マスタ API（ADMIN のみ）"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_roles
from app.database import get_db
from app.models import User
from app.models.enums import Role
from app.schemas.user_schema import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(require_roles(Role.ADMIN)),
):
    r = await db.execute(select(User).where(User.deleted_at.is_(None)).order_by(User.id))
    rows = r.scalars().all()
    return [UserResponse(id=u.id, login_id=u.login_id, name=u.name, role=u.role) for u in rows]
