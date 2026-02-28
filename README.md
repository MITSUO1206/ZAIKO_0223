# 在庫帳簿システム

Backend（FastAPI）+ Frontend（React/TypeScript）+ DB（PostgreSQL）の在庫帳簿システムです。  
**仕様の正本はリポジトリ内の Excel 仕様書「★要件定義書.xlsx」です。** 本READMEは起動手順・仮定一覧を補足します。

## 起動手順（やること）

1. **ターミナルを開き、このプロジェクトのフォルダ（リポジトリルート）に移動する。**

2. **次のコマンドを実行する。**

```bash
docker compose up --build
```

3. **起動完了まで待つ。**  
   - DB → Backend（マイグレーション＋シード）→ Frontend の順で起動します。  
   - ターミナルに **`Seed done.`** と表示されたらバックエンドの準備完了です（初回は数十秒かかることがあります）。

4. **ブラウザで http://localhost:5173 を開く。**

5. **下表のログインID・パスワードでログインする。**（シードで投入した利用者マスタ）

| ログインID | パスワード | 役割   |
|-----------|------------|--------|
| **admin** | **admin**  | 管理者（開発用） |
| mitsuo    | password   | 一般   |
| matsumoto | password   | 管理者 |
| nagahiro  | password   | 承認者 |
| aoki      | password   | 一般   |
| yasanaka  | password   | 承認者 |

※ 開発用に **admin / admin** で管理者ログインできます。それ以外はパスワード `password` です。

---

起動するサービス: **DB**（PostgreSQL 16 / 5432）、**Backend**（FastAPI / 8000）、**Frontend**（Vite / 5173）。バックエンド起動時にマイグレーションとシードが自動実行されます。

## 技術スタック

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL, JWT, bcrypt, pydantic v2
- **Frontend**: React, TypeScript, Vite, TanStack Query, React Hook Form, Zod, React Router, react-i18next, Tailwind CSS
- **Infra**: Docker / Docker Compose

## リポジトリ構成（モノレポ）

- `excel/` … 仕様書を置くだけ（実行時には参照しない）
- `backend/` … FastAPI アプリ
- `frontend/` … React アプリ
- `docker-compose.yml` … 起動定義
- `README.md` … 本ファイル

## 仕様の出典

- 機能要件・テーブル定義・PK/FK・状態遷移・画面入力定義・監査ログ要件は **Excel「★要件定義書.xlsx」** に準拠しています。
- Excel は開発時に参照するものであり、アプリの実行時に読み込む対象ではありません。

## 仮定一覧（Excel の曖昧・不足に対する対応）

以下のように仮定して実装しています。仕様が確定したら差し替え可能です。

| 項目 | 仮定内容 |
|------|----------|
| 取下げ | PENDING の帳簿のみ取下げ可能。取下げ時は `withdrawn_at` を設定し、在庫は変更しない。 |
| 差戻し | 「差戻し」は未実装。却下のみ（在庫は動かさない）。差戻し時に在庫を戻す処理は行わない。 |
| 出庫・払出の在庫不足 | 承認時に在庫不足の場合は **409 Conflict** で「在庫不足のため承認できません」を返す。 |
| ID 形式 | prefix 1文字 + 4桁連番（例: U0001, L0001）。採番は `id_sequences` テーブル + `SELECT FOR UPDATE`。 |
| 監査ログの hash | `sha256(prev_hash + action + table + target + before + after + actor + time)`。before/after は JSON キー順で安定化。 |
| 利用者マスタ | ADMIN のみ一覧参照可能。作成・編集・削除は今回スコープ外（一覧のみ）。 |
| 添付（attachments） | Excel に記載があっても、最初は「メタのみ」もスコープ外。必要なら別対応。 |

## 主な API

- `POST /auth/login` … ログイン（成否を login_logs に記録）
- `GET /auth/me` … 自分
- `POST /auth/password-reset-request` … パスワード再設定トークン発行
- `POST /auth/password-reset` … トークン＋新パスワードで再設定
- `GET/POST /items` … 在庫マスタ一覧・作成（型番/単価/安全在庫等対応）
- `GET/PATCH/DELETE /items/{id}` … 在庫マスタ詳細・更新・論理削除（削除理由クエリ可）
- `GET/POST /ledgers` … 帳簿一覧・作成（ロット/工程名/廃棄種別対応）
- `GET/PATCH /ledgers/{id}` … 帳簿詳細・更新（未承認のみ）
- `POST /ledgers/{id}/withdraw` … 取下げ
- `GET /ledgers/approval/pending` … 承認待ち一覧（APPROVER/ADMIN）
- `POST /ledgers/{id}/approve` … 承認
- `POST /ledgers/{id}/reject` … 却下
- `GET /users` … 利用者一覧（ADMIN のみ）
- `GET/POST /ledger-formats` … 帳簿フォーマット一覧・作成
- `POST /ledger-formats/pages` … 帳簿ページ追加
- `GET/POST /attachments` … 帳簿添付（メタ・ファイルアップロード）
- `GET/POST /notifications/settings` … 発注アラート設定
- `GET /notifications/alerts/check` … 安全在庫を下回っている品目
- `GET /reports/stock-transition` … 年間在庫推移
- `GET /reports/disposal` … 廃棄量・金額
- `POST /chat/query` … チャット照会（RAG + Gemini 2.0：文脈把握して回答。API キー未設定時はキーワード検索のみ）

## 統合テスト

承認により在庫が増減することを pytest で確認する統合テストがあります。

- 実行前に `docker compose up` で DB とシードが投入されていること。
- Backend コンテナ内で実行する例:

```bash
docker compose run --rm backend pytest tests/test_approval_stock_integration.py -v
```

※ テストは同じ PostgreSQL（inventory）に対して実行します。本番データと分けたい場合は別DB（例: inventory_test）を用意し、環境変数で接続先を切り替えてください。

## チャット照会（RAG + Gemini 2.0）

「チャット」画面の照会は、**RAG（検索で取得した在庫・帳簿を文脈）＋ Gemini 2.0 Flash** で自然言語に答えます。

**参照しているテーブル**
- **items**（在庫マスタ）: 品目コード・名前・型番・現在庫・保管場所・LOT・入庫数・入庫日 など
- **ledgers**（帳簿トランザクション）: 入庫/出庫/払い出し・数量・ロット・工程名・実施日・備考 など  

「先月の入庫は?」のように**日付・種別（入庫/出庫）**を含む質問では、直近90日分の帳簿や種別＝入庫の帳簿も自動で文脈に含め、Gemini が回答します。

- **API キーを設定する**: [Google AI Studio](https://aistudio.google.com/apikey) で API キーを発行し、起動時に環境変数 `GEMINI_API_KEY` を渡す。  
  - 例: **プロジェクトルート**（この README があるフォルダ直下）に `.env` を 1 つだけ作り、`GEMINI_API_KEY=あなたのキー` の 1 行を記載。Docker Compose はその `.env` を読み込む。

**Gemini API がつながらないときの注意（よくある原因）**

1. **エディタで保存していない**  
   `.env` を編集したら **必ず保存（Ctrl+S）** してください。アプリはディスクに書かれた内容を読むため、保存しないと古いキーのままです。保存後にバックエンドを再起動してください。

2. **.env の場所が違う**  
   使う `.env` は **プロジェクトルート 1 つだけ**です。`backend/` など別フォルダに `.env` を作ると、どれが読まれるか分からず接続できないことがあります。ルートの `.env` だけを使い、キーはそこに書いて保存してください。

- **未設定の場合**: キーワード検索のみで「該当件数＋リンク」を返す従来動作になります。その場合でも参照テーブルは上記の **items** と **ledgers** です。

## トラブルシューティング

- **http://localhost:8000 に接続できない（Connection Refused）**  
  → バックエンドが起動していません。プロジェクトルートで `docker compose up --build` を実行し、**3 サービス（db / backend / frontend）がすべて起動していること**を確認してください。バックエンドは起動完了後、http://localhost:8000/ で `{"message":"在庫帳簿API"}` を返します。

- **ログインAPIを手動で試す（PowerShell）**  
  バックエンド起動後、次のコマンドでログインできるか確認できます（`login_id` と `password` を JSON で渡します）。

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/auth/login" -Method Post -ContentType "application/json" -Body '{"login_id":"admin","password":"admin"}'
```

  成功すると `access_token` が返ります。401 の場合はログインIDまたはパスワードを確認してください。

## ライセンス・注意

- 本システムは業務利用を想定したサンプル実装です。本番利用時は認証・秘密鍵・CORS・DB 接続などを環境に合わせて設定してください。
