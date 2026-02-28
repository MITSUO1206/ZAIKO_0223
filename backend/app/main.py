"""FastAPI エントリポイント"""
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import health, auth_router, items_router, ledgers_router, approval_router, users_router, ledger_formats_router, attachments_router, notifications_router, reports_router, chat_router, disposals_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="在庫帳簿API",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ローカル（Vite プロキシで /api が剥がされる）用: プレフィックスなし
app.include_router(health.router)
app.include_router(auth_router.router)
app.include_router(items_router.router)
app.include_router(ledgers_router.router)
app.include_router(approval_router.router)
app.include_router(users_router.router)
app.include_router(ledger_formats_router.router)
app.include_router(attachments_router.router)
app.include_router(notifications_router.router)
app.include_router(reports_router.router)
app.include_router(chat_router.router)
app.include_router(disposals_router.router)

# ALB で 1URL 運用時: /api/* でバックエンドに来るため /api 付きでも応答する
api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth_router.router)
api_router.include_router(items_router.router)
api_router.include_router(ledgers_router.router)
api_router.include_router(approval_router.router)
api_router.include_router(users_router.router)
api_router.include_router(ledger_formats_router.router)
api_router.include_router(attachments_router.router)
api_router.include_router(notifications_router.router)
api_router.include_router(reports_router.router)
api_router.include_router(chat_router.router)
api_router.include_router(disposals_router.router)
app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "在庫帳簿API"}
