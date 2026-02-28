"""チャット照会（RAG + Gemini 2.0：文脈把握して在庫・帳簿・廃棄・イベントログを返す）

参照テーブル:
- items（在庫マスタ）: 品目コード・名前・型番・現在庫・単価・保管場所・LOT・入庫日 等
- ledgers（帳簿）: 入庫/出庫/払い出し/廃棄・数量・ロット・工程名・実施日・備考 等
- disposals（廃棄データ）: 廃棄品目・数量・単価・理由・廃棄日
- audit_logs（イベント・監査ログ）: 誰がいつ何をしたか（CREATE/UPDATE/DELETE/APPROVE）
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, or_, func, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import User, Item, Ledger, Disposal, AuditLog
from app.models.enums import LedgerType, ApprovalStatus

router = APIRouter(prefix="/chat", tags=["chat"])

# 種別ラベル
LEDGER_TYPE_LABEL = {
    LedgerType.INBOUND: "入庫",
    LedgerType.OUTBOUND: "出庫",
    LedgerType.ISSUE: "払い出し",
    LedgerType.DISPOSAL: "廃棄",
}
STATUS_LABEL = {
    ApprovalStatus.PENDING: "承認待ち",
    ApprovalStatus.APPROVED: "承認済",
    ApprovalStatus.REJECTED: "却下",
}
ACTION_LABEL = {"CREATE": "登録", "UPDATE": "更新", "DELETE": "削除", "APPROVE": "承認"}
TABLE_LABEL = {"items": "品目", "ledgers": "帳簿", "disposals": "廃棄", "attachments": "添付", "notification_settings": "通知設定", "ledger_formats": "帳簿様式", "ledger_pages": "帳簿ページ"}


def _item_to_text(i: Item) -> str:
    parts = [
        f"[品目ID: {i.id}]",
        f"商品番号: {i.code}",
        f"商品名: {i.name}",
        f"現在庫: {i.current_qty}",
    ]
    if i.unit_price is not None:
        parts.append(f"単価: {i.unit_price}")
    if i.model_number:
        parts.append(f"型番: {i.model_number}")
    if i.storage_place:
        parts.append(f"保管場所: {i.storage_place}")
    if i.last_lot:
        parts.append(f"LOT: {i.last_lot}")
    if i.last_inbound_qty is not None:
        parts.append(f"直近入庫数: {i.last_inbound_qty}")
    if i.last_inbound_date:
        parts.append(f"直近入庫日: {i.last_inbound_date}")
    return " | ".join(parts)


def _ledger_to_text(l: Ledger, item_code: str = "", item_name: str = "") -> str:
    kind = LEDGER_TYPE_LABEL.get(l.ledger_type, l.ledger_type.value)
    st = STATUS_LABEL.get(l.status, l.status.value)
    parts = [
        f"[帳簿ID: {l.id}]",
        f"種別: {kind}",
        f"品目: {item_code} {item_name}".strip() or f"品目ID: {l.item_id}",
        f"数量: {l.quantity}",
        f"状態: {st}",
    ]
    if l.lot:
        parts.append(f"ロット: {l.lot}")
    if l.process_name:
        parts.append(f"工程名: {l.process_name}")
    if l.ledger_date:
        parts.append(f"実施日: {l.ledger_date}")
    if l.notes:
        parts.append(f"備考: {l.notes}")
    return " | ".join(parts)


def _disposal_to_text(d: Disposal) -> str:
    parts = [
        f"[廃棄ID: {d.id}]",
        f"品目: {d.item_code} {d.item_name}",
        f"数量: {d.quantity_disposed}",
    ]
    if d.unit_price_at_disposal is not None:
        parts.append(f"単価: {d.unit_price_at_disposal}")
    if d.reason:
        parts.append(f"理由: {d.reason}")
    parts.append(f"廃棄日: {d.disposed_at}")
    return " | ".join(parts)


def _audit_to_text(a: AuditLog, actor_name: str = "") -> str:
    """監査ログ1件をRAG用の短い1行に（before/afterは要約のみ）"""
    action = ACTION_LABEL.get(a.action, a.action)
    table = TABLE_LABEL.get(a.table_name, a.table_name)
    who = actor_name or a.actor_id
    created = str(a.created_at)[:19] if a.created_at else ""
    parts = [f"[ログID: {a.id}]", f"操作: {action}", f"対象: {table} {a.target_id}", f"実施者: {who}", f"日時: {created}"]
    if a.after_data and isinstance(a.after_data, dict):
        summary = []
        for k in ("code", "name", "status", "quantity", "current_qty", "delete_reason"):
            if k in a.after_data and a.after_data[k] is not None:
                summary.append(f"{k}={a.after_data[k]}")
        if summary:
            parts.append("内容: " + ", ".join(summary[:5]))
    if a.before_data and isinstance(a.before_data, dict) and a.action == "UPDATE":
        summary = []
        for k in ("code", "name", "status", "current_qty"):
            if k in a.before_data and a.before_data[k] is not None:
                summary.append(f"{k}={a.before_data[k]}")
        if summary:
            parts.append("変更前: " + ", ".join(summary[:4]))
    return " | ".join(parts)


def _query_needs_audit(q: str) -> bool:
    """履歴・誰が・変更・承認・ログ・イベント・監査を聞いているか"""
    q_lower = (q or "").replace("?", "").replace("。", "")
    audit_words = ("履歴", "誰が", "誰がやった", "変更", "承認", "ログ", "イベント", "監査", "削除した", "登録した", "更新した", "操作")
    return any(w in q_lower for w in audit_words)


def _query_needs_time_or_type(q: str) -> tuple[bool, bool]:
    """「先月」「入庫」など日付・種別を意識した検索が必要か"""
    q_lower = q.replace("?", "").replace("。", "")
    time_words = ("先月", "今月", "先週", "今週", "先日", "昨日", "今日", "入庫日", "実施日", "履歴")
    type_words = ("入庫", "出庫", "払い出し", "廃棄")
    needs_time = any(w in q_lower for w in time_words)
    needs_type = any(w in q_lower for w in type_words)
    return needs_time, needs_type


def _query_needs_aggregate(q: str) -> bool:
    """「総在庫数」「合計」など集計・全体を聞く質問か"""
    q_lower = q.replace("?", "").replace("。", "")
    agg_words = ("総在庫", "総在庫数", "合計", "全体", "在庫数", "合計数", "合計在庫", "全品目", "ぜんぶ", "全部")
    return any(w in q_lower for w in agg_words)


def _query_needs_dashboard_summary(q: str) -> bool:
    """「傾向」「まとめ」「今の状況」「ダッシュボード」など集計サマリを聞く質問か"""
    q_lower = (q or "").replace("?", "").replace("。", "")
    summary_words = ("傾向", "トレンド", "まとめ", "要約", "今の状況", "ダッシュボード", "集計の概要", "注意点", "気になる点", "サマリ")
    return any(w in q_lower for w in summary_words)


async def _get_dashboard_summary_text(db: AsyncSession) -> str:
    """現在のKPI・安全在庫アラートをテキストで返す（チャットRAGの先頭に付与用）。"""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    next_m = month_start.month % 12 + 1
    year = month_start.year + (1 if next_m == 1 else 0)
    month_end = month_start.replace(year=year, month=next_m)

    r = await db.execute(select(func.count(Item.id)).where(Item.deleted_at.is_(None)))
    total_items = r.scalar() or 0
    r = await db.execute(
        select(
            func.coalesce(func.sum(Item.current_qty), 0).label("qty"),
            func.coalesce(func.sum(Item.current_qty * func.coalesce(Item.unit_price, 0)), 0).label("val"),
        ).where(Item.deleted_at.is_(None))
    )
    row = r.one()
    total_qty = int(row.qty)
    total_val = float(row.val) if row.val is not None else 0.0
    r = await db.execute(select(func.count(Ledger.id)).where(Ledger.status == ApprovalStatus.PENDING))
    pending = r.scalar() or 0
    r = await db.execute(
        select(func.count(Ledger.id)).where(
            Ledger.created_at >= month_start,
            Ledger.created_at < month_end,
        )
    )
    this_month_ledgers = r.scalar() or 0
    stmt = select(Ledger, Item.unit_price).join(Item, Ledger.item_id == Item.id).where(
        Ledger.ledger_type == LedgerType.DISPOSAL,
        Ledger.status == ApprovalStatus.APPROVED,
        Ledger.created_at >= month_start,
        Ledger.created_at < month_end,
    )
    r = await db.execute(stmt)
    rows = r.all()
    disp_qty = sum(l.quantity for l, _ in rows)
    disp_amt = sum(l.quantity * (float(up) if up is not None else 0) for l, up in rows)

    stmt = select(Item).where(
        Item.deleted_at.is_(None),
        Item.safety_stock > 0,
        Item.current_qty < Item.safety_stock,
    ).order_by(Item.current_qty.asc()).limit(20)
    r = await db.execute(stmt)
    alert_items = r.scalars().all()

    lines = [
        "【現在の集計サマリ（ダッシュボード）】",
        f"品目数: {total_items}",
        f"総現在庫数: {total_qty}",
        f"在庫金額（概算）: {total_val:.0f}",
        f"承認待ち帳簿: {pending}件",
        f"今月の帳簿件数: {this_month_ledgers}件",
        f"今月の廃棄: 数量 {disp_qty}、金額（概算）{disp_amt:.0f}",
    ]
    if alert_items:
        lines.append("安全在庫を下回っている品目:")
        for i in alert_items:
            lines.append(f"  - {i.code} {i.name}: 現在庫={i.current_qty}, 安全在庫={i.safety_stock}")
    else:
        lines.append("安全在庫を下回っている品目: なし")
    return "\n".join(lines)


async def _retrieve_for_rag(db: AsyncSession, query: str) -> tuple[list[Item], list[tuple[Ledger, Item | None]], list[Disposal], list[AuditLog], dict[str, str]]:
    """検索語で品目・帳簿・廃棄・イベントログを取得（RAG 用）。"""
    terms = [t.strip() for t in query.split() if t.strip()]
    needs_time, needs_type = _query_needs_time_or_type(query)
    needs_aggregate = _query_needs_aggregate(query)
    needs_disposal = "廃棄" in (query or "").replace("?", "").replace("。", "")
    needs_audit = _query_needs_audit(query)

    if not terms:
        r = await db.execute(
            select(Item).where(Item.deleted_at.is_(None)).order_by(Item.id).limit(20)
        )
        items = list(r.scalars().all())
        r2 = await db.execute(
            select(Ledger).where(Ledger.withdrawn_at.is_(None)).order_by(Ledger.id.desc()).limit(20)
        )
        ledgers = list(r2.scalars().all())
        r3 = await db.execute(select(Disposal).order_by(Disposal.disposed_at.desc()).limit(20))
        disposals = list(r3.scalars().all())
        r4 = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(25))
        audit_logs = list(r4.scalars().all())
    else:
        like = [f"%{t}%" for t in terms]
        cond_item = or_(
            *[Item.code.ilike(l) for l in like],
            *[Item.name.ilike(l) for l in like],
            *[Item.model_number.ilike(l) for l in like],
        )
        r = await db.execute(
            select(Item).where(Item.deleted_at.is_(None), cond_item).limit(15)
        )
        items = list(r.scalars().all())
        cond_ledger = or_(
            *[Ledger.notes.ilike(l) for l in like],
            *[Ledger.process_name.ilike(l) for l in like],
            *[Ledger.lot.ilike(l) for l in like],
        )
        r2 = await db.execute(
            select(Ledger).where(Ledger.withdrawn_at.is_(None), cond_ledger).order_by(Ledger.id.desc()).limit(15)
        )
        ledgers = list(r2.scalars().all())
        cond_disposal = or_(
            *[Disposal.item_code.ilike(f"%{t}%") for t in terms],
            *[Disposal.item_name.ilike(f"%{t}%") for t in terms],
            *[Disposal.reason.ilike(f"%{t}%") for t in terms],
        )
        r3 = await db.execute(select(Disposal).where(cond_disposal).order_by(Disposal.disposed_at.desc()).limit(15))
        disposals = list(r3.scalars().all())
        cond_audit = or_(
            *[AuditLog.action.ilike(f"%{t}%") for t in terms],
            *[AuditLog.table_name.ilike(f"%{t}%") for t in terms],
            *[AuditLog.target_id.ilike(f"%{t}%") for t in terms],
        )
        r4 = await db.execute(select(AuditLog).where(cond_audit).order_by(AuditLog.created_at.desc()).limit(20))
        audit_logs = list(r4.scalars().all())

    if needs_audit and len(audit_logs) < 35:
        r_audit = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(35))
        extra_audit = list(r_audit.scalars().all())
        seen_a = {x.id for x in audit_logs}
        for a in extra_audit:
            if a.id not in seen_a:
                seen_a.add(a.id)
                audit_logs.append(a)

    if needs_disposal and len(disposals) < 25:
        r_extra = await db.execute(select(Disposal).order_by(Disposal.disposed_at.desc()).limit(25))
        extra = list(r_extra.scalars().all())
        seen_d = {x.id for x in disposals}
        for d in extra:
            if d.id not in seen_d:
                seen_d.add(d.id)
                disposals.append(d)

    # 「総在庫数」「合計」など: 全品目を文脈に含めて LLM に合計を計算させる
    if needs_aggregate and len(items) < 50:
        r_all = await db.execute(
            select(Item).where(Item.deleted_at.is_(None)).order_by(Item.id).limit(100)
        )
        all_items = list(r_all.scalars().all())
        seen_ids = {i.id for i in items}
        for i in all_items:
            if i.id not in seen_ids:
                seen_ids.add(i.id)
                items.append(i)

    # 「先月の入庫は?」など: キーワードでヒットしなくても直近の帳簿（入庫なら種別=入庫）を文脈に含める
    if (needs_time or needs_type) and len(ledgers) < 20:
        since = (datetime.now(timezone.utc) - timedelta(days=90))
        stmt = select(Ledger).where(
            Ledger.withdrawn_at.is_(None),
            Ledger.created_at >= since,
        )
        if needs_type and "入庫" in query.replace("?", ""):
            stmt = stmt.where(Ledger.ledger_type == LedgerType.INBOUND)
        stmt = stmt.order_by(Ledger.id.desc()).limit(25)
        r_extra = await db.execute(stmt)
        extra_ledgers = list(r_extra.scalars().all())
        seen = {l.id for l in ledgers}
        for l in extra_ledgers:
            if l.id not in seen:
                seen.add(l.id)
                ledgers.append(l)

    # 帳簿に品目情報を紐付け（全品目を1回取得）
    all_item_ids = {l.item_id for l in ledgers}
    if all_item_ids:
        r_items = await db.execute(select(Item).where(Item.id.in_(all_item_ids)))
        item_map = {i.id: i for i in r_items.scalars().all()}
    else:
        item_map = {}
    for i in items:
        item_map.setdefault(i.id, i)
    ledger_with_item = [(l, item_map.get(l.item_id)) for l in ledgers]

    actor_ids = {a.actor_id for a in audit_logs}
    user_map: dict[str, str] = {}
    if actor_ids:
        r_u = await db.execute(select(User).where(User.id.in_(actor_ids)))
        for u in r_u.scalars().all():
            user_map[u.id] = u.name or u.login_id or u.id

    return items, ledger_with_item, disposals, audit_logs, user_map


def _build_rag_context(
    items: list[Item],
    ledger_with_item: list[tuple[Ledger, Item | None]],
    disposals: list[Disposal],
    audit_logs: list[AuditLog],
    user_map: dict[str, str],
) -> str:
    lines = ["=== 在庫マスタ（品目）==="]
    for i in items:
        lines.append(_item_to_text(i))
    lines.append("")
    lines.append("=== 帳簿（入出庫履歴）===")
    for l, item in ledger_with_item:
        code = item.code if item else ""
        name = item.name if item else ""
        lines.append(_ledger_to_text(l, code, name))
    if disposals:
        lines.append("")
        lines.append("=== 廃棄データ ===")
        for d in disposals:
            lines.append(_disposal_to_text(d))
    if audit_logs:
        lines.append("")
        lines.append("=== イベント・監査ログ（誰がいつ何をしたか）===")
        for a in audit_logs:
            lines.append(_audit_to_text(a, user_map.get(a.actor_id, "")))
    return "\n".join(lines)


def _gemini_rest_generate(api_key: str, model_id: str, text: str) -> tuple[bool, str]:
    """REST API で generateContent を呼ぶ。キーはヘッダーで送る（URL だとエンコードでずれる場合がある）。"""
    import httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
    payload = {"contents": [{"parts": [{"text": text}]}]}
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, json=payload, headers=headers)
        if r.status_code != 200:
            return False, r.text or f"HTTP {r.status_code}"
        data = r.json()
        cands = data.get("candidates") or []
        if not cands:
            return False, "応答が空です"
        parts = (cands[0].get("content") or {}).get("parts") or []
        if not parts:
            return False, "応答が空です"
        return True, (parts[0].get("text") or "").strip()
    except Exception as e:
        return False, str(e)


def _test_gemini_connection() -> tuple[bool, str, bool]:
    """Gemini API キーで接続テスト。REST で直接呼ぶ（キーが有効なら確実に通る）。"""
    api_key = (settings.gemini_api_key or "").strip()
    key_configured = len(api_key) > 0
    if not api_key:
        return False, (
            "API キーがサーバーに渡っていません。.env を docker-compose.yml と同じフォルダに置き、"
            "docker compose down のあと docker compose up で再起動してください。"
        ), False
    for model_id in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"):
        ok, err = _gemini_rest_generate(api_key, model_id, "接続テスト")
        if ok:
            return True, "", True
        if "API key not valid" in err or "API_KEY_INVALID" in err or "403" in err or "401" in err:
            return False, (
                "Google がキーを無効と判定しています。AI Studio で新しいキーを発行し、.env を書き換えて再起動してください。"
            ), True
    return False, err or "接続できませんでした", True


def _call_gemini(context: str, user_query: str) -> str:
    """Gemini で文脈付き応答を生成（REST API 直接呼び出し）"""
    api_key = (settings.gemini_api_key or "").replace("\ufeff", "").replace("\r", "").strip()
    if not api_key:
        return ""

    system = """あなたは在庫帳簿システムのアシスタントです。
参照データの先頭に「【現在の集計サマリ（ダッシュボード）】」がある場合、それは品目数・総在庫・承認待ち・今月の廃棄・安全在庫アラートなどの現在の状況です。
「まとめ」「今の状況」「傾向」「注意点」を聞かれたときは、この集計サマリを必ず使って答えてください。サマリがあるのに「情報がありません」「いずれにもありません」と答えてはいけません。
以下の「在庫マスタ」「帳簿」「廃棄データ」「イベント・監査ログ」および「現在の集計サマリ」だけを根拠に答えてください。データにないことは推測せず「データにはありません」と答えてください。
「総在庫数」「合計」を聞かれた場合は、在庫マスタの「現在庫」を合計して数値で答えてください。
廃棄について聞かれた場合は「廃棄データ」を参照して答えてください。
「誰が」「いつ」「変更」「承認」「履歴」「ログ」など操作履歴を聞かれた場合は「イベント・監査ログ」を参照して答えてください。
回答は簡潔に。品目ID・帳簿ID・廃棄ID・ログIDがある場合は「品目 P0001」「帳簿 L0002」のように言及してください。"""

    prompt = f"""{system}

【参照データ】
{context}

【ユーザーの質問】
{user_query}
"""

    for model_id in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"):
        ok, text = _gemini_rest_generate(api_key, model_id, prompt)
        if ok and text:
            return text
    return ""


@router.get("/gemini-status")
async def gemini_status(user: User = Depends(get_current_user)):
    """Gemini API キーの接続可否を返す。key_suffix でバックエンドが読んだキー末尾を照合できる。"""
    api_key = (settings.gemini_api_key or "").strip()
    key_suffix = api_key[-4:] if len(api_key) >= 4 else ""
    ok, err, key_configured = _test_gemini_connection()
    if ok:
        return {"connected": True, "message": "Gemini API に接続できました", "key_configured": True, "key_suffix": key_suffix}
    return {"connected": False, "message": err or "接続に失敗しました", "key_configured": key_configured, "key_suffix": key_suffix}


@router.post("/query")
async def chat_query(
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: User = Depends(get_current_user),
):
    """自然言語の問い合わせを RAG（検索）＋ Gemini 2.0 で文脈把握して回答する。"""
    query = (body.get("query") or body.get("q") or "").strip()
    if not query:
        return {"answer": "検索語を入力してください。", "links": []}

    # RAG: 検索で関連する品目・帳簿・廃棄・イベントログを取得
    items, ledger_with_item, disposals, audit_logs, user_map = await _retrieve_for_rag(db, query)

    # リンク用（フロントで品目・帳簿・廃棄・監査へ飛ぶ）
    links = [{"type": "item", "id": i.id, "label": f"{i.code} {i.name}"} for i in items]
    for l, _ in ledger_with_item:
        links.append({"type": "ledger", "id": l.id, "label": f"帳簿 {l.id}"})
    for d in disposals:
        links.append({"type": "disposal", "id": d.id, "label": f"廃棄 {d.id} {d.item_code}"})
    for a in audit_logs:
        links.append({"type": "audit", "id": a.id, "label": f"ログ {a.id} {ACTION_LABEL.get(a.action, a.action)} {a.table_name} {a.target_id}"})

    context = _build_rag_context(items, ledger_with_item, disposals, audit_logs, user_map)
    dashboard_summary_injected = False
    summary_text = ""
    if _query_needs_dashboard_summary(query):
        summary_text = await _get_dashboard_summary_text(db)
        context = summary_text + "\n\n" + context
        dashboard_summary_injected = True
    answer_llm = _call_gemini(context, query)

    if answer_llm:
        # サマリを注入したのに「情報がありません」と返ってきた場合は、サマリ本文で答える
        if dashboard_summary_injected and summary_text and ("いずれにもありません" in answer_llm or "情報がありません" in answer_llm or "見つかりません" in answer_llm):
            answer = "現在の状況のまとめです。\n\n" + summary_text.replace("【現在の集計サマリ（ダッシュボード）】", "【集計サマリ】")
        else:
            answer = answer_llm
    else:
        # API キー未設定 or エラー時: まとめ・傾向を聞いていたらサマリを返す
        if dashboard_summary_injected and summary_text:
            answer = "現在の状況のまとめです。\n\n" + summary_text.replace("【現在の集計サマリ（ダッシュボード）】", "【集計サマリ】")
        elif not items and not ledger_with_item and not disposals and not audit_logs:
            answer = f"「{query}」に該当する在庫・帳簿・ログは見つかりませんでした。"
        else:
            answer = f"「{query}」に該当する結果を{len(links)}件見つけました。下記リンクから詳細を確認できます。"

    return {"answer": answer, "links": links}
