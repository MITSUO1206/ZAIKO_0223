"""承認・却下・在庫反映（サービス層で一括処理、監査ログ含む）"""
import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Ledger, Item, StockTx, ApprovalHistory, User
from app.models.enums import ApprovalStatus, LedgerType
from app.services.id_service import next_id
from app.services.audit_service import append_audit, get_prev_hash


def _signature_hash(ledger_id: str, status: str, approved_by: str, comment: str | None, created_at: str) -> str:
    payload = f"{ledger_id}|{status}|{approved_by}|{comment or ''}|{created_at}"
    return hashlib.sha256(payload.encode()).hexdigest()


async def approve_ledger(
    session: AsyncSession,
    ledger_id: str,
    approver: User,
    comment: str | None = None,
) -> Ledger:
    r = await session.execute(
        select(Ledger).where(Ledger.id == ledger_id, Ledger.withdrawn_at.is_(None))
    )
    ledger = r.scalar_one_or_none()
    if not ledger:
        raise ValueError("帳簿が見つかりません")
    if ledger.status != ApprovalStatus.PENDING:
        raise ValueError("未承認の帳簿のみ承認できます")
    r2 = await session.execute(select(Item).where(Item.id == ledger.item_id))
    item = r2.scalar_one_or_none()
    if not item:
        raise ValueError("品目が見つかりません")
    if ledger.ledger_type in (LedgerType.OUTBOUND, LedgerType.ISSUE, LedgerType.DISPOSAL):
        if item.current_qty < ledger.quantity:
            raise ValueError("在庫不足のため承認できません")
    delta = ledger.quantity if ledger.ledger_type == LedgerType.INBOUND else -ledger.quantity
    created_at = datetime.now(timezone.utc)
    created_at_str = created_at.isoformat()
    sig_hash = _signature_hash(ledger_id, ApprovalStatus.APPROVED.value, approver.id, comment, created_at_str)
    ah_id = await next_id(session, "A")
    session.add(ApprovalHistory(
        id=ah_id,
        ledger_id=ledger_id,
        status=ApprovalStatus.APPROVED,
        approved_by=approver.id,
        signature_hash=sig_hash,
        comment=comment,
        created_at=created_at,
    ))
    ledger.status = ApprovalStatus.APPROVED
    stx_id = await next_id(session, "S")
    session.add(StockTx(
        id=stx_id,
        ledger_id=ledger_id,
        item_id=ledger.item_id,
        quantity_delta=delta,
        created_at=created_at,
    ))
    item.current_qty += delta
    await session.flush()
    before_audit = {"status": ApprovalStatus.PENDING.value, "item_current_qty": item.current_qty - delta}
    after_audit = {"status": ApprovalStatus.APPROVED.value, "item_current_qty": item.current_qty}
    await append_audit(session, "APPROVE", "ledgers", ledger_id, approver.id, before_data=before_audit, after_data=after_audit)
    await session.refresh(ledger)
    return ledger


async def reject_ledger(
    session: AsyncSession,
    ledger_id: str,
    approver: User,
    comment: str | None = None,
) -> Ledger:
    r = await session.execute(
        select(Ledger).where(Ledger.id == ledger_id, Ledger.withdrawn_at.is_(None))
    )
    ledger = r.scalar_one_or_none()
    if not ledger:
        raise ValueError("帳簿が見つかりません")
    if ledger.status != ApprovalStatus.PENDING:
        raise ValueError("未承認の帳簿のみ却下できます")
    created_at = datetime.now(timezone.utc)
    created_at_str = created_at.isoformat()
    sig_hash = _signature_hash(ledger_id, ApprovalStatus.REJECTED.value, approver.id, comment, created_at_str)
    ah_id = await next_id(session, "A")
    session.add(ApprovalHistory(
        id=ah_id,
        ledger_id=ledger_id,
        status=ApprovalStatus.REJECTED,
        approved_by=approver.id,
        signature_hash=sig_hash,
        comment=comment,
        created_at=created_at,
    ))
    ledger.status = ApprovalStatus.REJECTED
    await session.flush()
    before_audit = {"status": ApprovalStatus.PENDING.value}
    after_audit = {"status": ApprovalStatus.REJECTED.value}
    await append_audit(session, "APPROVE", "ledgers", ledger_id, approver.id, before_data=before_audit, after_data=after_audit)
    await session.refresh(ledger)
    return ledger
