"""監査ログ（before/after + ハッシュチェーン）"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.services.id_service import next_id


def _sort_key(o: Any) -> str:
    """JSONB用キー順ソートで安定化"""
    if o is None:
        return "null"
    if isinstance(o, dict):
        return json.dumps({k: _sort_key(v) for k, v in sorted(o.items())}, sort_keys=True)
    if isinstance(o, list):
        return json.dumps([_sort_key(x) for x in o], sort_keys=True)
    return json.dumps(o, sort_keys=True)


def _compute_hash(prev_hash: str | None, action: str, table_name: str, target_id: str,
                  before_data: dict | None, after_data: dict | None, actor_id: str, created_at: str) -> str:
    before_str = _sort_key(before_data)
    after_str = _sort_key(after_data)
    payload = f"{prev_hash or ''}|{action}|{table_name}|{target_id}|{before_str}|{after_str}|{actor_id}|{created_at}"
    return hashlib.sha256(payload.encode()).hexdigest()


async def get_prev_hash(session: AsyncSession) -> str | None:
    """直近の監査ログのhashを取得"""
    r = await session.execute(
        select(AuditLog.hash).order_by(AuditLog.id.desc()).limit(1)
    )
    return r.scalar_one_or_none()


async def append_audit(
    session: AsyncSession,
    action: str,
    table_name: str,
    target_id: str,
    actor_id: str,
    before_data: dict | None = None,
    after_data: dict | None = None,
) -> AuditLog:
    """監査ログ1件追加（ハッシュチェーン）"""
    prev = await get_prev_hash(session)
    created_at = datetime.now(timezone.utc).isoformat()
    log_id = await next_id(session, "G")
    h = _compute_hash(prev, action, table_name, target_id, before_data, after_data, actor_id, created_at)
    log = AuditLog(
        id=log_id,
        action=action,
        table_name=table_name,
        target_id=target_id,
        before_data=before_data,
        after_data=after_data,
        actor_id=actor_id,
        prev_hash=prev,
        hash=h,
        created_at=datetime.now(timezone.utc),
    )
    session.add(log)
    await session.flush()
    return log
