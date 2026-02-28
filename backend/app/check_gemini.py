"""GEMINI_API_KEY が効いているかコマンドラインで確認する。

backend フォルダで、仮想環境を有効にしてから:
  .\.venv\Scripts\activate
  python -m app.check_gemini
（.env はプロジェクトルートにある想定）
"""
import os
import sys
from pathlib import Path

# プロジェクトルートの .env を必ず使う（import 前に手動で読み込む）
_backend = Path(__file__).resolve().parent.parent  # backend
_root = _backend.parent  # プロジェクトルート（在庫管理アプリ）
sys.path.insert(0, str(_backend))
_env_path = _root / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                if k.strip() == "GEMINI_API_KEY":
                    os.environ["GEMINI_API_KEY"] = v.strip().strip('"').strip("'")
                    break
os.chdir(_root)
from app.config import settings


def main() -> None:
    env_path = _root / ".env"
    print("GEMINI_API_KEY を確認しています...")
    print(f"  読んでいる .env: {env_path.resolve()}")
    api_key = (settings.gemini_api_key or "").strip()
    key_len = len(api_key)
    print(f"  キー: {'設定あり (' + str(key_len) + ' 文字)' if key_len else '未設定'}")
    if key_len > 0:
        ok_start = api_key.startswith("AIzaSy")
        print(f"  形式: {'OK (AIzaSy で始まっています)' if ok_start else '要確認 (通常は AIzaSy で始まります)'}")
        if key_len >= 4:
            print(f"  キー末尾（照合）: ****{api_key[-4:]}")
    if not api_key:
        print("  結果: NG - キーが読み込まれていません（.env の場所を確認）")
        return

    # REST API で直接試す（キーが有効なら確実に通る）
    from app.routers.chat_router import _gemini_rest_generate
    last_err = ""
    for model_id in ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"):
        ok, err = _gemini_rest_generate(api_key, model_id, "Hi")
        if ok:
            print(f"  結果: OK - Gemini API に接続できました（モデル: {model_id}）")
            return
        last_err = err or ""
    print(f"  結果: NG - {last_err[:300]}{'...' if len(last_err) > 300 else ''}")
    if "API key" in last_err or "API_KEY" in last_err or "403" in last_err or "401" in last_err:
        print("        → キーが無効か制限されています。AI Studio で新規キーを発行し、.env を上書き保存して再実行してください。")


if __name__ == "__main__":
    main()
