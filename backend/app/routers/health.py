"""ヘルスチェック"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health(db: AsyncSession = Depends(get_db)):
    """DB接続含むヘルスチェック"""
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
