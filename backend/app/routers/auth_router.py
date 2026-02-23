"""認証API"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_current_user, verify_password
from app.database import get_db
from app.models import User, LoginLog
from app.schemas.auth import LoginRequest, TokenResponse, UserMe
from app.services.id_service import next_id

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    r = await db.execute(
        select(User).where(User.login_id == form.login_id, User.deleted_at.is_(None))
    )
    user = r.scalar_one_or_none()
    if not user:
        log_id = await next_id(db, "H")
        db.add(LoginLog(id=log_id, login_id=form.login_id, success=False, ip_address=ip, user_agent=ua))
        await db.flush()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ログインIDまたはパスワードが違います")
    if not verify_password(form.password, user.hashed_password):
        log_id = await next_id(db, "H")
        db.add(LoginLog(id=log_id, login_id=form.login_id, success=False, ip_address=ip, user_agent=ua))
        await db.flush()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ログインIDまたはパスワードが違います")
    log_id = await next_id(db, "H")
    db.add(LoginLog(id=log_id, login_id=user.login_id, success=True, ip_address=ip, user_agent=ua))
    await db.flush()
    token = create_access_token(sub=user.login_id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserMe)
async def me(user: User = Depends(get_current_user)):
    return UserMe(id=user.id, login_id=user.login_id, name=user.name, role=user.role.value)


@router.post("/password-reset-request")
async def password_reset_request(
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """パスワード再設定用トークン発行（メール送信はスタブ：トークンをレスポンスで返す開発用）"""
    from datetime import datetime, timezone, timedelta
    from app.models import PasswordResetToken
    import secrets
    login_id = body.get("login_id") or body.get("email")
    if not login_id:
        raise HTTPException(400, "login_id を指定してください")
    r = await db.execute(select(User).where(User.login_id == login_id, User.deleted_at.is_(None)))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "ユーザーが見つかりません")
    token_str = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    db.add(PasswordResetToken(id=token_str, user_id=user.id, expires_at=expires))
    await db.flush()
    return {"message": "トークンを発行しました。本番ではメール送信します。", "token": token_str}


@router.post("/password-reset")
async def password_reset(
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """トークンと新パスワードで再設定"""
    from datetime import datetime, timezone
    from app.models import PasswordResetToken
    from passlib.context import CryptContext
    token_str = body.get("token")
    new_password = body.get("new_password")
    if not token_str or not new_password:
        raise HTTPException(400, "token と new_password を指定してください")
    r = await db.execute(select(PasswordResetToken).where(PasswordResetToken.id == token_str))
    pr = r.scalar_one_or_none()
    if not pr or pr.used_at or (pr.expires_at and datetime.now(timezone.utc) > pr.expires_at):
        raise HTTPException(400, "トークンが無効または期限切れです")
    r2 = await db.execute(select(User).where(User.id == pr.user_id))
    user = r2.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "ユーザーが見つかりません")
    user.hashed_password = CryptContext(schemes=["bcrypt"], deprecated="auto").hash(new_password)
    pr.used_at = datetime.now(timezone.utc)
    await db.flush()
    return {"message": "パスワードを更新しました"}
