"""pytest 設定（asyncio）"""
# 非同期テストは pytest.ini の asyncio_mode = auto と
# asyncio_default_fixture_loop_scope = function で実行。
# カスタム event_loop フィクスチャは削除（pytest-asyncio のデフォルトを使用）。

import os
import socket

# ホストから pytest を実行したときは "db" が解決できないので、localhost に差し替える。
# （Docker の db が ports: 5432 で公開されている前提。docker compose up -d で DB を起動しておく）
try:
    socket.getaddrinfo("db", 5432)
except socket.gaierror:
    os.environ["database_url"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/inventory"
    os.environ["database_url_sync"] = "postgresql://postgres:postgres@localhost:5432/inventory"
