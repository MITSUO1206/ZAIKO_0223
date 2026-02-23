"""承認・却下 API（APPROVER/ADMIN）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models import User, Ledger
from app.models.enums import Role, ApprovalStatus
from app.schemas.ledger_schema import LedgerResponse, ApproveRejectBody
from app.services.approval_service import approve_ledger, reject_ledger

router = APIRouter(prefix="/ledgers", tags=["approval"])


def _ledger_response(l: Ledger) -> LedgerResponse:
    return LedgerResponse(
        id=l.id,
        item_id=l.item_id,
        ledger_type=l.ledger_type,
        quantity=l.quantity,
        status=l.status,
        created_by=l.created_by,
        created_at=l.created_at,
        updated_at=l.updated_at,
        notes=l.notes,
    )


@router.get("/approval/pending", response_model=list[LedgerResponse])
async def list_pending(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(Role.APPROVER, Role.ADMIN)),
):
    r = await db.execute(
        select(Ledger).where(
            Ledger.status == ApprovalStatus.PENDING,
            Ledger.withdrawn_at.is_(None),
        ).order_by(Ledger.id.desc())
    )
    return [_ledger_response(x) for x in r.scalars().all()]


@router.post("/{ledger_id}/approve", response_model=LedgerResponse)
async def approve(
    ledger_id: str,
    body: ApproveRejectBody | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(Role.APPROVER, Role.ADMIN)),
):
    comment = body.comment if body else None
    try:
        ledger = await approve_ledger(db, ledger_id, user, comment=comment)
        return _ledger_response(ledger)
    except ValueError as e:
        if "在庫不足" in str(e):
            raise HTTPException(409, detail=str(e))
        raise HTTPException(400, detail=str(e))


@router.post("/{ledger_id}/reject", response_model=LedgerResponse)
async def reject(
    ledger_id: str,
    body: ApproveRejectBody | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(Role.APPROVER, Role.ADMIN)),
):
    comment = body.comment if body else None
    try:
        ledger = await reject_ledger(db, ledger_id, user, comment=comment)
        return _ledger_response(ledger)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))
