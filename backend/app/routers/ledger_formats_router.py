"""帳簿フォーマット・帳簿ページ API"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User, LedgerFormat, LedgerPage
from app.schemas.ledger_format_schema import LedgerFormatCreate, LedgerFormatResponse, LedgerPageCreate, LedgerPageResponse
from app.services.id_service import next_id
from app.services.audit_service import append_audit

router = APIRouter(prefix="/ledger-formats", tags=["ledger-formats"])


@router.get("", response_model=list[LedgerFormatResponse])
async def list_formats(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    r = await db.execute(select(LedgerFormat).order_by(LedgerFormat.id))
    return list(r.scalars().all())


@router.post("", response_model=LedgerFormatResponse, status_code=201)
async def create_format(body: LedgerFormatCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    fid = await next_id(db, "F")
    fmt = LedgerFormat(id=fid, name=body.name, version=body.version, input_fields=body.input_fields, has_comment_field=body.has_comment_field, pdf_layout=body.pdf_layout)
    db.add(fmt)
    await append_audit(db, "CREATE", "ledger_formats", fid, user.id, before_data=None, after_data=body.model_dump())
    await db.flush()
    await db.refresh(fmt)
    return fmt


@router.get("/{format_id}", response_model=LedgerFormatResponse)
async def get_format(format_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    r = await db.execute(select(LedgerFormat).where(LedgerFormat.id == format_id))
    fmt = r.scalar_one_or_none()
    if not fmt:
        raise HTTPException(404, "フォーマットが見つかりません")
    return fmt


@router.post("/pages", response_model=LedgerPageResponse, status_code=201)
async def create_page(body: LedgerPageCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    r = await db.execute(select(LedgerFormat).where(LedgerFormat.id == body.format_id))
    if not r.scalar_one_or_none():
        raise HTTPException(400, "フォーマットが存在しません")
    pid = await next_id(db, "P")
    page = LedgerPage(id=pid, format_id=body.format_id, memo=body.memo)
    db.add(page)
    await append_audit(db, "CREATE", "ledger_pages", pid, user.id, before_data=None, after_data=body.model_dump())
    await db.flush()
    await db.refresh(page)
    return page
