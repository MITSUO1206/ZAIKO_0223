# ローカルで Docker から立ち上げる

DB・バックエンド・フロントをまとめて Docker Compose で起動し、ブラウザで **admin / admin** でログインできるようにする手順です。

---

## 前提

- **Docker Desktop** がインストールされ、起動していること
- プロジェクトのルート（`在庫管理アプリ` フォルダ）で作業する

---

## 手順

### 1. プロジェクトルートに移動

PowerShell で:

```powershell
cd "C:\Users\満尾和博\OneDrive\デスクトップ\在庫管理アプリ"
```

### 2. .env ファイル（任意）

バックエンドは `env_file: .env` を参照しますが、docker-compose で DB 接続などは環境変数で上書きしているため、**なくても起動できます**。

Gemini（チャット機能）を使う場合は、ルートに `.env` を作り、次のように書いておきます。

```
GEMINI_API_KEY=あなたのAPIキー
```

空の `.env` や、この行がない場合でも起動は可能です。

### 3. ビルドして起動

```powershell
docker compose up --build
```

- 初回はイメージのビルドで 2〜5 分かかることがあります。
- ログに `Uvicorn running on http://0.0.0.0:8000` と `Local: http://localhost:5173/` などが出たら起動完了です。

### 4. ブラウザで確認

- **フロント**: http://localhost:5173  
- **ログイン**: ログインID **admin** / パスワード **admin**

### 5. 止めるとき

同じターミナルで **Ctrl+C** を押し、必要なら:

```powershell
docker compose down
```

---

## よくあるトラブル

| 現象 | 対処 |
|------|------|
| ポート 5173 や 5432 が使われている | 他のアプリで同じポートを使っていないか確認。変更する場合は `docker-compose.yml` の `ports` を編集。 |
| backend で `entrypoint.sh: no such file or directory` | Windows で CRLF になっている可能性。プロジェクトの `backend/entrypoint.sh` は、Dockerfile 内で `sed -i 's/\r$//'` しているので、通常はイメージを再ビルドすれば解消。 |
| ログインできない | バックエンドのログに `Seed done.` が出ているか確認。出ていなければ `docker compose down` のあと `docker compose up --build` でやり直す。 |

---

## 構成のイメージ

```
ブラウザ → http://localhost:5173 (frontend)
                ↓ /api をプロキシ
           http://backend:8000 (backend)
                ↓
           postgres:5432 (db)
```

フロントは開発サーバー（Vite）で、`/api` へのリクエストをバックエンドにプロキシしています。

---

## 本番のファイル（コンテナ内）で pytest を実行する

**同じ Docker イメージ・同じ環境**（`database_url` が `db:5432`）でテストを回したい場合は、**backend コンテナのなか**で pytest を実行します。本番に近い設定で検証できます。

### 前提

- **db が起動していること**（`docker compose up -d` で db だけでも可）

### コマンド（プロジェクトルートで）

```powershell
docker compose run --rm --entrypoint python backend -m pytest tests/ -v
```

- **--entrypoint python** … コンテナの通常の起動処理（alembic → seed → uvicorn）をやめ、`python` を直接実行する
- その後の **-m pytest tests/ -v** が python への引数になる
- **run** … 一時的に backend コンテナを起動する（通常の `up` の backend とは別プロセス）
- **--rm** … 実行後にコンテナを削除する
- コンテナ内では **database_url が `db:5432`** のため、同じ Docker ネットワーク上の db に接続される
- **tests/** で test_main_app / test_database などが実行される

### 特定のテストだけ実行する

```powershell
docker compose run --rm --entrypoint python backend -m pytest tests/test_database.py tests/test_main_app.py -v
```

### わかること

- **本番と同じイメージ・同じ環境**（Python バージョン・依存・env）でテストが通るか
- **DB 接続が `db` ホストで問題ないか**（コンテナ内では `db` が解決する）

