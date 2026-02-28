# backend フォルダ配下の構成と役割

backend は **FastAPI + SQLAlchemy（非同期） + PostgreSQL** で動く在庫帳簿 API です。ファイル・フォルダごとに「何をしているか」を名前とともに箇条書きでまとめます。

---

## ルート直下（backend/）

- **Dockerfile**  
  - コンテナイメージの定義。Python 3.12-slim、PostgreSQL クライアント、requirements.txt で依存インストール、entrypoint.sh の改行修正（CRLF→LF）と実行権付与、起動は entrypoint.sh に委譲。

- **entrypoint.sh**  
  - コンテナ起動時に実行するスクリプト。`alembic upgrade head` で DB マイグレーション → `python -m app.seed` で初期データ投入 → `uvicorn app.main:app --host 0.0.0.0 --port 8000` で API サーバー起動。

- **requirements.txt**  
  - Python の依存パッケージ一覧（FastAPI、SQLAlchemy、asyncpg、alembic、JWT、passlib など）。

- **alembic.ini**  
  - Alembic（DB マイグレーション）の設定ファイル。script_location、ログ設定など。接続 URL は env.py で環境変数から上書きされる。

- **pytest.ini**  
  - pytest の設定（テストの探し方・オプションなど）。

---

## alembic/（DB マイグレーション）

- **env.py**  
  - Alembic の実行環境。config の DB URL を `settings.database_url_sync` で上書きし、全モデルを読み込んでからマイグレーションを実行。

- **script.py.mako**  
  - 新規マイグレーションスクリプトを生成するときのテンプレート。

- **versions/**  
  - マイグレーションスクリプトを格納するフォルダ。
  - **001_initial.py** … 初回スキーマ（ユーザー、品目、帳簿、在庫トランザクション、承認履歴など）。
  - **002_ledger_withdrawn_at.py** … 帳簿に `withdrawn_at` などを追加。
  - **003_item_ledger_extend.py** … 品目・帳簿まわりの拡張。
  - **004_new_tables.py** … 新規テーブル追加。
  - **005_item_last_lot_inbound.py** … 品目の最終ロット入庫関連。
  - **006_disposals.py** … 廃棄（disposals）関連テーブル。

---

## app/（アプリ本体）

### app/main.py の詳細

#### 全体から見た main.py の役割

バックエンド全体のなかで、**main.py** は「**HTTP の入口**」です。

- **やっていること**  
  フロントや ALB から届いたリクエストを「どのルート（URL）で受け取るか」を決め、CORS などの共通設定をまとめてかけています。  
  実際の処理（ログイン・品目一覧・帳簿の CRUD など）は **routers/** や **auth.py** などにあり、main.py はそれらを **1 つの FastAPI アプリに組み込む**役割です。

- **位置づけ**  
  - **entrypoint.sh** が `uvicorn app.main:app` でサーバーを起動する → 起動時に読まれるのが **main.py**  
  - **config.py** の設定（CORS など）を main.py が使う  
  - **routers/** の各ルーターを main.py が `include_router` で登録する  

つまり「**設定を読み、ルートを集めて、API サーバーとして動かす土台**」が main.py です。  
個々のビジネスロジックは main.py には書かず、routers や services に任せています。

---

**用語の補足**

- **「1 つの FastAPI アプリに組み込む」とは**  
  - ルート（エンドポイント）は **routers/** でバラバラに定義されています（health.py に `/health`、auth_router.py に `/auth/login` など）。  
  - そのままでは「バラバラのルーター」で、**どれも 1 つのサーバーとして動いていません**。  
  - main.py で **1 つの `app = FastAPI(...)`** を作り、`app.include_router(health.router)` のように**全部くっつける**ことで、**1 つのプロセス（uvicorn）で全部の URL が扱える**ようになります。  
  - これを「ルーターを 1 つの FastAPI アプリに組み込む」と言っています。

- **「設定を読み、ルートを集めて、API サーバーとして動かす土台」とは**  
  - **設定を読む** … `settings.cors_origins_list` など、config.py の値を main.py が読み、CORS ミドルウェアなどに渡している。  
  - **ルートを集める** … 上のように、各ルーターを `include_router` で 1 つの `app` に登録している。  
  - **API サーバーとして動かす土台** … `uvicorn app.main:app` が起動するのは「main.py の `app`」だけ。その `app` にルートと設定が全部載っているので、**main.py が「土台」**で、ここがなければサーバーとして成り立たない、という意味です。

---

**イメージできるように（図と流れ）**

```
  【バラバラの状態】                    【main.py で 1 つに】

  health.py      →  /health              ┌─────────────────────────────────┐
  auth_router.py →  /auth/login          │  app = FastAPI()                 │
  items_router   →  /items               │  + CORS など設定                │
  ...            →  ...                  │  + include_router(health)        │
                                         │  + include_router(auth_router)   │
  どれも「単体」で、                     │  + include_router(items_router)  │
  サーバーはまだ動いていない             │  + ...                           │
                                         └──────────────┬──────────────────┘
                                                       │
                                                       ▼
                                         uvicorn がこの app を 1 つだけ起動
                                         → 1 つのポート(8000)で全部の URL が応答
```

**具体的にいうと**

- **uvicorn** は「Python の Web サーバー」です。`entrypoint.sh` で `uvicorn app.main:app --host 0.0.0.0 --port 8000` と実行しているので、**ポート 8000 で 1 つのプロセス**が動いています。
- その 1 つのプロセスが持っているのが、main.py で作った **1 つの `app`** です。health も auth も items も、全部この `app` に `include_router` でくっつけてあるので、「ポート 8000 に来たリクエストは、全部この `app` が受け取る」状態になっています。
- だから、
  - `http://localhost:8000/health` にアクセス → 同じプロセス・同じポートの `app` が受け取り、health の処理が動く
  - `http://localhost:8000/auth/login` にアクセス → 同じプロセス・同じポートの `app` が受け取り、auth の処理が動く
  - `http://localhost:8000/items` にアクセス → 同じプロセス・同じポートの `app` が受け取り、items の処理が動く
- **別々のサーバーや別々のポート**を用意しているわけではなく、**1 つのポート 8000 の 1 つのプロセス**が、パス（/health, /auth/login, /items, ...）を見て「どれに当たるか」を振り分けている、という意味です。

**「どれに当たるか」の振り分けはどうやっているか**

FastAPI が**内部で「ルート表」を持っている**からです。

1. **ルートの登録**  
   `app.include_router(health.router)` や `app.include_router(auth_router.router)` を実行すると、FastAPI はそれぞれのルーターに書かれた「**メソッド + パス**」と「**そのときに呼ぶ関数**」を**1 つの表**に積み増しします。  
   - 例: health.router は `prefix="/health"` で `@router.get("")` なので → **GET /health** → `health()` 関数  
   - 例: auth_router は `prefix="/auth"` で `@router.post("/login")` なので → **POST /auth/login** → `login()` 関数  
   同じように、items_router なら GET /items, POST /items などが表に追加されていきます。

2. **リクエストが来たとき**  
   リクエストの「**HTTP メソッド（GET / POST など）**」と「**URL のパス（/health, /auth/login など）**」を FastAPI が受け取り、上の**ルート表**と照らし合わせます。「このメソッド + このパス」に一致する登録を探し、見つかったら**その登録に対応した関数を 1 つだけ呼ぶ**、という動きです。

3. **誰がやっているか**  
   この「表を持って、リクエストごとに一致するルートを探して関数を呼ぶ」のは、**FastAPI（と Starlette）の内部**がやっています。main.py で `include_router` した時点で表ができ、uvicorn がリクエストを app に渡すと、app がその表で振り分けて関数を実行します。  
   つまり「**どの URL をどの関数に当てるか**」は、`@router.get("")` や `@router.post("/login")` と `prefix` の組み合わせで決まり、それを FastAPI がまとめて「ルート表」として持って、振り分けに使っている、という仕組みです。

1. フロントや ALB から「`POST /api/auth/login`」が届く。
2. **main.py の app** が受け取る（uvicorn が app を動かしているので、全部ここに届く）。
3. app が「このパスはどのルーターか？」と見る → `/api/auth/login` なら **auth_router** に渡す。
4. auth_router の「ログイン処理」が動き、レスポンスを返す。

つまり「**main.py の app = 玄関。届いたリクエストを、どの部屋（ルーター）に回すか振り分けている**」と考えるとイメージしやすいです。部屋の中の細かい処理（DB に聞く・パスワード照合など）は routers や services が担当し、main.py は「玄関と振り分け」だけです。

---

以下は main.py の中身を「エントリ」「CORS」「プレフィックスなしルート」「/api 付きルート」に分けた説明です。

---

#### 1. エントリ（アプリと lifespan）

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI(
    title="在庫帳簿API",
    lifespan=lifespan,
)
```

- **FastAPI(...)** でアプリ本体を作成。`title` は OpenAPI（/docs）のタイトル。
- **lifespan** は起動〜終了のライフサイクル。終了時に `engine.dispose()` で DB エンジンのコネクションを閉じる。

---

#### 2. CORS（クロスオリジン）

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- ブラウザから別オリジン（例: フロント 5173 → API 8000）へリクエストするときに CORS が必要。
- **allow_origins** … 許可するオリジン（`config.py` の `cors_origins` をリスト化したもの）。
- **allow_credentials=True** … クッキー・Authorization ヘッダー付きを許可（ログイン後 API に必要）。
- **allow_methods / allow_headers** … 全メソッド・全ヘッダー許可。

---

#### 3. プレフィックスなしルート（ローカル用）

```python
app.include_router(health.router)
app.include_router(auth_router.router)
app.include_router(items_router.router)
# ... 他も同様
```

**なぜ必要？**  
ローカルでは、フロントが「`/api/auth/login`」と叩くと、**Vite が「/api」を取って**バックエンドに「`/auth/login`」だけ送ります。  
だからバックエンドには **「/api なし」のパス**で届く。この「/api なし」を受け取るために、プレフィックスなしでルーターを登録している。

---

#### 4. /api 付きルート（本番・ALB 用）

```python
api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
# ... 他も同様
app.include_router(api_router)
```

**なぜ必要？**  
本番（ALB）では、フロントが「`https://ALBのURL/api/auth/login`」と叩くと、ALB は**パスをそのまま**バックエンドに渡す。  
だからバックエンドには **「/api 付き」のパス**（`/api/auth/login`）で届く。その「/api 付き」を受け取るために、`prefix="/api"` のルーターに同じルートを登録している。

---

#### 一言で言うと

| 環境 | バックエンドに届くパス | だから |
|------|------------------------|--------|
| ローカル（Vite が /api を取る） | `/auth/login` など **/api なし** | プレフィックスなしの登録が必要 |
| 本番（ALB はそのまま渡す） | `/api/auth/login` など **/api 付き** | /api 付きの登録が必要 |

「届くパスが違う」ので、**両方の形**でルートを用意している。

---

#### 5. ルートパス /

```python
@app.get("/")
async def root():
    return {"message": "在庫帳簿API"}
```

**何をしているか**  
ブラウザや curl で「API のアドレスだけ」を開いたとき（例: `http://localhost:8000/`）に、この処理が動きます。パスは **`/`** だけ（何も付けない）のときです。

**返るもの**  
`{"message": "在庫帳簿API"}` という JSON を返します。

**何に使うか**  
- 「サーバーが起動しているか」の簡単な確認
- ALB やロードバランサーのヘルスチェックの対象にすることもできる（このアプリでは DB 確認付きの `/health` を主に使っている）
- 人が「この URL が API だ」とひと目で分かるようにするため

つまり「トップ（/）にアクセスしたら、API ですよというメッセージを返す」だけの処理です。

---

#### まとめ（main.py で有効なパス）

| 種類 | 例 |
|------|-----|
| プレフィックスなし（ローカル） | `/health`, `/auth/login`, `/items` |
| /api 付き（ALB） | `/api/health`, `/api/auth/login`, `/api/items` |
| ルート | `/` → `{"message": "在庫帳簿API"}` |

---

### ルート直下

- **main.py**  
  - FastAPI のエントリポイント。CORS 設定、ルーター登録（プレフィックスなし＋`/api` 付きの二重登録で ALB の 1URL 対応）、ルート `/` の応答。  
  - 詳しくは下の **[app/main.py の詳細](#appmainpy-の詳細)** を参照。

- **config.py**  
  - 環境変数から設定を読む（DB URL、Gemini API キー、JWT secret、CORS 許可オリジンなど）。pydantic-settings の `Settings`。

- **database.py**  
  - 非同期 DB エンジン・セッションの作成と、FastAPI 用の `get_db` 依存性（コミット・ロールバック・クローズの扱い）。

- **auth.py**  
  - 認証まわり。パスワード検証、JWT トークン発行、Bearer トークンから現在ユーザー取得（`get_current_user`）、ロール制限（`require_roles`、RequireAdmin / RequireApprover / RequireUser）。

- **seed.py**  
  - 起動時などに実行する初期データ投入。admin ユーザー、品目、帳簿、在庫トランザクション、承認履歴、添付・監査ログなどのサンプルデータを作成。

- **check_gemini.py**  
  - Gemini API の接続・動作確認用のユーティリティ（チャット照会で利用する API キーなどの確認用）。

---

## app/models/（DB モデル・テーブル定義）

- **__init__.py**  
  - 各モデルをまとめてインポートし、`__all__` で公開。Alembic や他モジュールから `from app.models import User, Item, ...` で参照するため。

- **enums.py**  
  - 共通の列挙型（ロール、帳簿種別、承認ステータスなど）。

- **user.py**  
  - ユーザーテーブル（ログイン ID、パスワードハッシュ、ロール、削除日時など）。

- **item.py**  
  - 品目マスタ。

- **ledger.py**  
  - 帳簿（台帳）の定義。

- **ledger_page.py**  
  - 帳簿のページ（帳簿と 1 対多など）。

- **ledger_format.py**  
  - 帳簿フォーマット（表示形式など）。

- **stock_tx.py**  
  - 在庫トランザクション（入出庫・移動などの履歴）。

- **approval_history.py**  
  - 承認履歴。

- **id_sequence.py**  
  - 連番・ID 採番用のテーブル。

- **attachment.py**  
  - 添付ファイルのメタ情報。

- **audit_log.py**  
  - 監査ログ。

- **notification_setting.py**  
  - 通知設定。

- **notification_log.py**  
  - 通知送信ログ。

- **password_reset_token.py**  
  - パスワードリセット用トークン。

- **login_log.py**  
  - ログイン履歴。

- **disposal.py**  
  - 廃棄（disposal）関連のモデル。

---

## app/routers/（API エンドポイント）

各ファイルは FastAPI の `APIRouter` を定義し、main.py でプレフィックスなしと `/api` 付きの両方に include されている。

- **health.py**  
  - ヘルスチェック。`/health` で DB 接続を含む死活確認。

- **auth_router.py**  
  - ログイン・ログアウト・トークン発行など認証 API。

- **items_router.py**  
  - 品目マスタの CRUD。

- **ledgers_router.py**  
  - 帳簿の CRUD・一覧。

- **ledger_formats_router.py**  
  - 帳簿フォーマットの API。

- **approval_router.py**  
  - 承認申請・承認操作などの API。

- **users_router.py**  
  - ユーザー管理（一覧・作成・更新など）。管理者向け。

- **attachments_router.py**  
  - 添付ファイルのアップロード・取得・削除。

- **notifications_router.py**  
  - 通知設定・通知履歴の API。

- **reports_router.py**  
  - レポート・集計系 API。

- **chat_router.py**  
  - チャット照会（LLM 利用）用 API。

- **disposals_router.py**  
  - 廃棄（disposal）の API。

---

## app/schemas/（リクエスト・レスポンスの型）

Pydantic モデルで、API の入出力の形とバリデーションを定義。

- **auth.py**  
  - ログインリクエスト・トークン応答など認証まわりのスキーマ。

- **user_schema.py**  
  - ユーザー作成・更新・一覧用のスキーマ。

- **item_schema.py**  
  - 品目用のスキーマ。

- **ledger_schema.py**  
  - 帳簿用のスキーマ。

- **ledger_format_schema.py**  
  - 帳簿フォーマット用のスキーマ。

- **disposal_schema.py**  
  - 廃棄用のスキーマ。

- **notification_schema.py**  
  - 通知まわりのスキーマ。

- **attachment_schema.py**  
  - 添付ファイルまわりのスキーマ。

---

## app/services/（ビジネスロジック）

- **id_service.py**  
  - 連番・ID の採番ロジック（id_sequence などを利用）。

- **audit_service.py**  
  - 監査ログの記録処理。

- **approval_service.py**  
  - 承認フローまわりのロジック（申請・承認・却下など）。

---

## tests/（テスト）

- **conftest.py**  
  - pytest のフィクスチャ（テスト用 DB セッション、クライアント、認証済みユーザーなど）を定義。

- **test_approval_stock_integration.py**  
  - 承認と在庫まわりの結合テスト。

---

## まとめ（フォルダ単位）

| フォルダ／ファイル | 役割 |
|--------------------|------|
| **backend/** 直下 | コンテナ定義・起動スクリプト・依存・Alembic/pytest 設定 |
| **alembic/** | DB マイグレーションの設定と versions（スキーマ変更履歴） |
| **app/** | FastAPI アプリ本体（設定・DB・認証・seed） |
| **app/models/** | SQLAlchemy モデル（テーブル定義・列挙型） |
| **app/routers/** | エンドポイントごとのルーター（health, auth, items, ledgers, approval, users, attachments, notifications, reports, chat, disposals） |
| **app/schemas/** | リクエスト・レスポンスの Pydantic スキーマ |
| **app/services/** | 採番・監査・承認などのビジネスロジック |
| **tests/** | pytest のフィクスチャと結合テスト |
