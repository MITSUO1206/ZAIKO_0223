"""帳簿添付ファイル API（メタのみ保存。実ファイルはローカル/S3等に保存）"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, Form, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Attachment, Ledger
from app.schemas.attachment_schema import AttachmentResponse
from app.services.id_service import next_id
from app.services.audit_service import append_audit

router = APIRouter(prefix="/attachments", tags=["attachments"])

# 開発用：アップロードファイル保存先（本番ではS3等）
UPLOAD_DIR = "/tmp/inventory_uploads"


@router.get("", response_model=list[AttachmentResponse])
async def list_attachments(ledger_id: Annotated[str | None, Query()] = None, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Attachment)
    if ledger_id:
        stmt = stmt.where(Attachment.ledger_id == ledger_id)
    r = await db.execute(stmt.order_by(Attachment.id.desc()))
    return list(r.scalars().all())


@router.post("", response_model=AttachmentResponse, status_code=201)
async def upload_attachment(
    ledger_id: Annotated[str, Form()],
    title: Annotated[str | None, Form()] = None,
    file_type: Annotated[str | None, Form()] = None,
    file: UploadFile | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = await db.execute(select(Ledger).where(Ledger.id == ledger_id))
    if not r.scalar_one_or_none():
        raise HTTPException(400, "帳簿が存在しません")
    import os
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    aid = await next_id(db, "T")
    file_path = f"{UPLOAD_DIR}/{aid}"
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1] or ".bin"
        file_path = f"{UPLOAD_DIR}/{aid}{ext}"
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(400, "ファイルは10MB以内にしてください")
        with open(file_path, "wb") as f:
            f.write(content)
    att = Attachment(id=aid, ledger_id=ledger_id, file_path=file_path, title=title, file_type=file_type or (file.content_type if file else None))
    db.add(att)
    await append_audit(db, "CREATE", "attachments", aid, user.id, before_data=None, after_data={"ledger_id": ledger_id, "title": title})
    await db.flush()
    await db.refresh(att)
    return att
