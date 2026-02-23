"""初期データ投入（利用者・在庫マスタ・帳簿・在庫トランザクション・承認履歴・添付・監査ログ）"""
import asyncio
import os
import sys
from datetime import datetime, timezone

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import AsyncSessionLocal, Base, engine
from app.models import (
    User,
    Item,
    IdSequence,
    Ledger,
    StockTx,
    ApprovalHistory,
    Attachment,
    AuditLog,
)
from app.models.enums import Role, LedgerType, ApprovalStatus

# 日付ヘルパー（JST 9:00 等を UTC に）
def dt(*a):
    return datetime(*a, tzinfo=timezone.utc)


def hash_password(plain: str) -> str:
    from passlib.context import CryptContext
    return CryptContext(schemes=["bcrypt"], deprecated="auto").hash(plain)


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # FK の依存順: disposals → ledgers なので disposals を先に削除
        for table in ["audit_logs", "attachments", "approval_history", "stock_tx", "disposals", "ledgers", "items", "users", "login_logs", "id_sequences"]:
            await session.execute(text(f"DELETE FROM {table}"))
        await session.commit()

    async with AsyncSessionLocal() as session:
        # ID採番
        session.add(IdSequence(prefix="U", next_value=7))
        session.add(IdSequence(prefix="P", next_value=6))
        session.add(IdSequence(prefix="L", next_value=6))
        session.add(IdSequence(prefix="T", next_value=6))
        session.add(IdSequence(prefix="A", next_value=6))
        session.add(IdSequence(prefix="F", next_value=6))
        session.add(IdSequence(prefix="AU", next_value=6))
        session.add(IdSequence(prefix="H", next_value=1))  # ログイン監査 (login_logs)
        session.add(IdSequence(prefix="I", next_value=1))
        for prefix in ["S", "G", "D"]:
            session.add(IdSequence(prefix=prefix, next_value=1))

        # 利用者マスタ（仕様: U0001〜U0005 + 開発用 admin）
        def u(uid, login_id, name, role, password="password"):
            session.add(User(id=uid, login_id=login_id, hashed_password=hash_password(password), name=name, role=role))
        u("U0001", "mitsuo", "満尾 和博", Role.USER)
        u("U0002", "matsumoto", "松本 ゆう子", Role.ADMIN)
        u("U0003", "nagahiro", "長弘 恒一", Role.APPROVER)
        u("U0004", "aoki", "青木 恒一", Role.USER)
        u("U0005", "yasanaka", "安仲 恒一", Role.APPROVER)
        u("U0006", "admin", "管理者", Role.ADMIN, "admin")  # 開発用: admin / admin でログイン可

        # 在庫マスタ（P0001〜P0005）
        products = [
            ("P0001", "AB-460-1", "ニトリル手袋（青）M", "NTG-M-BLU", "消耗品", "箱", 980, 10, "2F備品庫-A1", 24),
            ("P0002", "CF-112-3", "クリアファイル A4", "CF-A4", "文具", "枚", 12, 200, "2F備品庫-B2", 650),
            ("P0003", "ET-009-1", "エタノール 99.5% 500mL", "ET-500", "試薬", "本", 520, 5, "危険物庫-棚3", 8),
            ("P0004", "TB-210-2", "チューブ 1.5mL", "TB-1.5", "消耗品", "袋", 450, 20, "2F備品庫-C4", 15),
            ("P0005", "LB-033-9", "ラベルシール 24面", "LB-24", "文具", "冊", 360, 3, "2F備品庫-B1", 2),
        ]
        for item_id, code, name, model_number, category, unit, unit_price, safety_stock, storage_place, current_qty in products:
            session.add(Item(
                id=item_id,
                code=code,
                name=name,
                model_number=model_number,
                category=category,
                unit=unit,
                unit_price=unit_price,
                safety_stock=safety_stock,
                storage_place=storage_place,
                current_qty=current_qty,
                deleted_at=None,
            ))

        # 帳簿トランザクション（L0001〜L0005）
        # id, 種別, item_id, 数量, lot, process_name, 実施日, status, created_by, created_at
        ledgers_data = [
            ("L0001", LedgerType.INBOUND, "P0001", 30, "LOT-202602-001", None, dt(2026, 2, 20), ApprovalStatus.APPROVED, "U0002", dt(2026, 2, 22, 9, 0, 0)),
            ("L0002", LedgerType.OUTBOUND, "P0002", 100, None, "事務", dt(2026, 2, 21), ApprovalStatus.PENDING, "U0001", dt(2026, 2, 22, 9, 0, 0)),
            ("L0003", LedgerType.ISSUE, "P0003", 1, "ET-202602-A", "実験A", dt(2026, 2, 22), ApprovalStatus.PENDING, "U0001", dt(2026, 2, 22, 9, 0, 0)),
            ("L0004", LedgerType.INBOUND, "P0004", 10, "TB-202602-07", None, dt(2026, 2, 18), ApprovalStatus.REJECTED, "U0001", dt(2026, 2, 22, 9, 0, 0)),
            ("L0005", LedgerType.OUTBOUND, "P0001", 5, "LOT-202602-001", "現場", dt(2026, 2, 19), ApprovalStatus.APPROVED, "U0003", dt(2026, 2, 22, 9, 0, 0)),
        ]
        for lid, ltype, item_id, qty, lot, process_name, ledger_date, status, created_by, created_at in ledgers_data:
            session.add(Ledger(
                id=lid,
                item_id=item_id,
                ledger_type=ltype,
                quantity=qty,
                lot=lot,
                process_name=process_name,
                ledger_date=ledger_date,
                status=status,
                created_by=created_by,
                created_at=created_at,
            ))
        await session.flush()  # ledgers を先に DB に書き、attachments の FK を満たす

        # 在庫トランザクション（T0001〜T0005）：入庫=+, 出庫/払い出し=-
        stock_txs_data = [
            ("T0001", "L0001", "P0001", 30),
            ("T0002", "L0002", "P0002", -100),
            ("T0003", "L0003", "P0003", -1),
            ("T0004", "L0004", "P0004", 10),
            ("T0005", "L0005", "P0001", -5),
        ]
        for tid, ledger_id, item_id, delta in stock_txs_data:
            session.add(StockTx(id=tid, ledger_id=ledger_id, item_id=item_id, quantity_delta=delta))

        # 承認履歴（A0001〜A0005）
        approvals_data = [
            ("A0001", "L0001", "U0003", ApprovalStatus.APPROVED, dt(2026, 2, 20, 16, 12, 0), "sha256:2f8da91c"),
            ("A0002", "L0004", "U0003", ApprovalStatus.REJECTED, dt(2026, 2, 18, 18, 40, 0), "sha256:0c1a98fe"),
            ("A0003", "L0005", "U0002", ApprovalStatus.APPROVED, dt(2026, 2, 19, 10, 5, 0), "sha256:9b77c3dd"),
            ("A0004", "L0002", "U0003", ApprovalStatus.APPROVED, dt(2026, 2, 21, 15, 20, 0), "sha256:7aa1e210"),
            ("A0005", "L0003", "U0003", ApprovalStatus.APPROVED, dt(2026, 2, 22, 11, 2, 0), "sha256:3e4c1b0a"),
        ]
        for aid, ledger_id, approved_by, status, created_at, sig in approvals_data:
            session.add(ApprovalHistory(
                id=aid,
                ledger_id=ledger_id,
                status=status,
                approved_by=approved_by,
                signature_hash=sig,
                created_at=created_at,
            ))

        # 添付ファイル（F0001〜F0005）
        attachments_data = [
            ("F0001", "L0001", "納品書_20260220_P0001.pdf", "/drive/ledger/L0001/納品書.pdf", dt(2026, 2, 20, 16, 0, 0)),
            ("F0002", "L0002", "出庫依頼_20260221_P0002.pdf", "/drive/ledger/L0002/出庫依頼.pdf", dt(2026, 2, 21, 9, 10, 0)),
            ("F0003", "L0003", "実験記録_20260222_P0003.pdf", "/drive/ledger/L0003/実験記録.pdf", dt(2026, 2, 22, 9, 20, 0)),
            ("F0004", "L0004", "入庫申請_20260218_P0004.pdf", "/drive/ledger/L0004/入庫申請.pdf", dt(2026, 2, 18, 17, 5, 0)),
            ("F0005", "L0005", "出庫記録_20260219_P0001.pdf", "/drive/ledger/L0005/出庫記録.pdf", dt(2026, 2, 19, 10, 0, 0)),
        ]
        for fid, ledger_id, title, file_path, created_at in attachments_data:
            session.add(Attachment(id=fid, ledger_id=ledger_id, title=title, file_path=file_path, created_at=created_at))

        # 監査ログ（AU0001〜AU0005）：ハッシュチェーン用のプレースホルダ
        chain = [None, "seed_au0001", "seed_au0002", "seed_au0003", "seed_au0004", "seed_au0005"]
        audit_data = [
            ("AU0001", "CREATE", "帳簿トランザクション", "L0002", None, {"帳簿種別": "出庫", "商品ID": "P0002", "数量": 100}, "U0001", dt(2026, 2, 21, 9, 5, 0)),
            ("AU0002", "APPROVE", "帳簿トランザクション", "L0001", {"承認ステータス": "未承認"}, {"承認ステータス": "承認済"}, "U0003", dt(2026, 2, 20, 16, 12, 0)),
            ("AU0003", "UPDATE", "在庫マスタ", "P0001", {"現在在庫数": "-"}, {"現在在庫数": 24}, "U0002", dt(2026, 2, 20, 16, 15, 0)),
            ("AU0004", "APPROVE", "帳簿トランザクション", "L0004", {"承認ステータス": "未承認"}, {"承認ステータス": "却下"}, "U0003", dt(2026, 2, 18, 18, 40, 0)),
            ("AU0005", "CREATE", "添付ファイル", "F0003", None, {"関連帳簿ID": "L0003", "ファイル名": "実験記録_..."}, "U0001", dt(2026, 2, 22, 9, 20, 0)),
        ]
        for i, (auid, action, table_name, target_id, before_data, after_data, actor_id, created_at) in enumerate(audit_data):
            session.add(AuditLog(
                id=auid,
                action=action,
                table_name=table_name,
                target_id=target_id,
                before_data=before_data,
                after_data=after_data,
                actor_id=actor_id,
                prev_hash=chain[i],
                hash=chain[i + 1],
                created_at=created_at,
            ))

        await session.commit()
    print("Seed done.")


if __name__ == "__main__":
    asyncio.run(seed())
