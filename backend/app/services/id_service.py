"""ID採番（prefix+連番、SELECT FOR UPDATE）"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.id_sequence import IdSequence


async def next_id(session: AsyncSession, prefix: str) -> str:
    """
    prefix: U, I, L, S, A, G など1文字推奨。4桁ゼロパッド連番。
    例: U -> U0001, U0002
    """
    p = (prefix or "X").upper()[:1]
    row = await session.execute(
        select(IdSequence).where(IdSequence.prefix == p).with_for_update()
    )
    seq = row.scalar_one_or_none()
    if seq is None:
        seq = IdSequence(prefix=p, next_value=1)
        session.add(seq)
        await session.flush()
    n = seq.next_value
    seq.next_value = n + 1
    await session.flush()
    return f"{p}{n:04d}"
