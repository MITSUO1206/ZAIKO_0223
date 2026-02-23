"""FastAPI エントリポイント"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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


@app.get("/")
async def root():
    return {"message": "在庫帳簿API"}
