# Fargate でバックエンド・DB を動かしログインできるようにする

フロントは既に Fargate で稼働している前提。ここでは **RDS（PostgreSQL）の作成** → **バックエンドの ECR/ECS デプロイ** → **フロントの API 向き先変更** までをまとめます。

- リージョン: **ap-northeast-1（東京）**
- 既存: クラスター `inventory-cluster`、フロントサービス `inventory-service`、フロント用タスク定義 `inventory-task`（ポート 5173）

---

## 前提・変数

PowerShell で一度に設定:

```powershell
$env:AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
$env:REGION = "ap-northeast-1"
$env:VPC_ID = (aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text --region $env:REGION)
$env:SUBNET_IDS = (aws ec2 describe-subnets --filters "Name=vpc-id,Values=$env:VPC_ID" --query "Subnets[*].SubnetId" --output text --region $env:REGION) -replace '\s+', ','
$env:SUBNET_1 = ($env:SUBNET_IDS -split ',')[0]
```

RDS のマスタパスワードは **任意の強めのパスワード** を決めておく（例: `MyDbPass123!`）。メモしておく。

---

# Step 1: RDS（PostgreSQL）の作成

## 1-1. RDS 用セキュリティグループ（後でバックエンド SG から 5432 を許可する）

バックエンド用 SG は Step 2 で作るため、ここでは **RDS 用 SG だけ作成** し、あとから「バックエンド SG からの 5432」を追加する方法で進めます。

```powershell
# RDS 用 SG
$env:SG_RDS_NAME = "rds-inventory-sg"
$env:SG_RDS_ID = (aws ec2 create-security-group `
  --group-name $env:SG_RDS_NAME `
  --description "RDS for inventory backend" `
  --vpc-id $env:VPC_ID `
  --region $env:REGION `
  --query GroupId --output text)
Write-Host "SG_RDS_ID=$env:SG_RDS_ID"
```

いったんインバウンドは追加しない。**Step 2 でバックエンド用 SG を作成したあと**、その SG からの 5432 を許可する。

## 1-2. DB サブネットグループ（デフォルト VPC のサブネットを使う）

```powershell
# サブネット ID を 2 つ取得（RDS は複数 AZ 用に 2 つ以上推奨）
$subnets = (aws ec2 describe-subnets --filters "Name=vpc-id,Values=$env:VPC_ID" --query "Subnets[*].SubnetId" --output text --region $env:REGION) -split '\s+'
$env:DB_SUBNET_GROUP_NAME = "inventory-db-subnet"
aws rds create-db-subnet-group `
  --db-subnet-group-name $env:DB_SUBNET_GROUP_NAME `
  --db-subnet-group-description "Inventory RDS subnet" `
  --subnet-ids $subnets `
  --region $env:REGION
```

既に同名がある場合はエラーでよい（スキップ）。

## 1-3. RDS インスタンス作成

**マスタパスワード** を環境変数に設定してから実行（必ず自分のパスワードに変更）:

```powershell
$env:RDS_MASTER_PASSWORD = "MyDbPass123!"   # 任意の強めのパスワードに変更
$env:RDS_MASTER_USER = "postgres"
$env:DB_NAME = "inventory"
```

```powershell
aws rds create-db-instance `
  --db-instance-identifier inventory-db `
  --db-instance-class db.t3.micro `
  --engine postgres `
  --engine-version 16 `
  --master-username $env:RDS_MASTER_USER `
  --master-user-password $env:RDS_MASTER_PASSWORD `
  --allocated-storage 20 `
  --db-name $env:DB_NAME `
  --vpc-security-group-ids $env:SG_RDS_ID `
  --db-subnet-group-name $env:DB_SUBNET_GROUP_NAME `
  --no-publicly-accessible `
  --region $env:REGION
```

作成完了まで **5〜10 分** かかります。

```powershell
# ステータス確認（available になるまで待つ）
aws rds describe-db-instances --db-instance-identifier inventory-db --query "DBInstances[0].DBInstanceStatus" --output text --region $env:REGION
```

## 1-4. RDS エンドポイント取得

```powershell
$env:RDS_ENDPOINT = (aws rds describe-db-instances --db-instance-identifier inventory-db --query "DBInstances[0].Endpoint.Address" --output text --region $env:REGION)
Write-Host "RDS_ENDPOINT=$env:RDS_ENDPOINT"
```

接続文字列の例（後でバックエンドの環境変数に使う）:

- **async:** `postgresql+asyncpg://postgres:MyDbPass123!@<RDS_ENDPOINT>:5432/inventory`
- **sync:** `postgresql://postgres:MyDbPass123!@<RDS_ENDPOINT>:5432/inventory`

---

# Step 2: バックエンドの ECR・イメージ・ECS

## 2-1. バックエンド用 ECR リポジトリ

```powershell
$env:REPO_BACKEND = "inventory-ledger-backend"
aws ecr create-repository --repository-name $env:REPO_BACKEND --region $env:REGION --image-scanning-configuration scanOnPush=true
```

## 2-2. バックエンド用セキュリティグループ（8000 を開放）

```powershell
$env:SG_BACKEND_NAME = "ecs-backend-inventory"
$env:SG_BACKEND_ID = (aws ec2 create-security-group `
  --group-name $env:SG_BACKEND_NAME `
  --description "Backend 8000 for inventory" `
  --vpc-id $env:VPC_ID `
  --region $env:REGION `
  --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id $env:SG_BACKEND_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region $env:REGION
Write-Host "SG_BACKEND_ID=$env:SG_BACKEND_ID"
```

## 2-3. RDS に「バックエンド SG からの 5432」を許可

```powershell
aws ec2 authorize-security-group-ingress `
  --group-id $env:SG_RDS_ID `
  --protocol tcp --port 5432 `
  --source-group $env:SG_BACKEND_ID `
  --region $env:REGION
```

## 2-4. ECR ログイン・バックエンドイメージのビルドと push

プロジェクトルート（`在庫管理アプリ`）で:

```powershell
aws ecr get-login-password --region $env:REGION | docker login --username AWS --password-stdin "$env:AWS_ACCOUNT_ID.dkr.ecr.$env:REGION.amazonaws.com"
docker build -t $env:REPO_BACKEND`:latest -f backend/Dockerfile ./backend
docker tag "${env:REPO_BACKEND}:latest" "${env:AWS_ACCOUNT_ID}.dkr.ecr.${env:REGION}.amazonaws.com/${env:REPO_BACKEND}:latest"
docker push "${env:AWS_ACCOUNT_ID}.dkr.ecr.${env:REGION}.amazonaws.com/${env:REPO_BACKEND}:latest"
```

**注意:** `backend/entrypoint.sh` が Windows で CRLF になっていると起動失敗することがあります。その場合は Git で改行を LF に:  
`git config core.autocrlf input` のうえで `backend/entrypoint.sh` を再度保存するか、WSL 上でビルドしてください。

## 2-5. バックエンド用ロググループ・タスク定義（コンソール推奨）

ロググループ:

```powershell
aws logs create-log-group --log-group-name "/ecs/inventory-backend-task" --region $env:REGION
```

タスク定義は **Windows の file パス問題を避けるため AWS コンソール** で作成するのが確実です。

1. **ECS** → **タスク定義** → **新しいタスク定義の作成** → **JSON タブ**。
2. 以下を貼り付け、**置き換え** する:
   - `YOUR_ACCOUNT_ID` → 手元の 12 桁アカウント ID
   - `YOUR_RDS_ENDPOINT` → Step 1-4 の `RDS_ENDPOINT`（例: `inventory-db.xxxxx.ap-northeast-1.rds.amazonaws.com`）
   - `YOUR_RDS_PASSWORD` → RDS のマスタパスワード（1-3 で設定したもの）
   - `YOUR_FRONTEND_URL` → フロントの URL（例: `http://13.231.183.94:5173`）。フロントの Public IP がまだなら仮で `http://localhost:5173` にしておき、あとでタスク定義の「新しいリビジョン」で更新可能。

```json
{
  "family": "inventory-backend-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.ap-northeast-1.amazonaws.com/inventory-ledger-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        { "name": "database_url", "value": "postgresql+asyncpg://postgres:YOUR_RDS_PASSWORD@YOUR_RDS_ENDPOINT:5432/inventory" },
        { "name": "database_url_sync", "value": "postgresql://postgres:YOUR_RDS_PASSWORD@YOUR_RDS_ENDPOINT:5432/inventory" },
        { "name": "secret_key", "value": "change-me-in-production-use-env" },
        { "name": "cors_origins", "value": "http://localhost:5173,http://127.0.0.1:5173,YOUR_FRONTEND_URL" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/inventory-backend-task",
          "awslogs-region": "ap-northeast-1"
        }
      }
    }
  ]
}
```

`YOUR_FRONTEND_URL` はフロントの Public IP が分かっているなら `http://<そのIP>:5173` にしておく（CORS 用）。

## 2-6. バックエンドサービス作成

```powershell
aws ecs create-service `
  --cluster inventory-cluster `
  --service-name inventory-backend-service `
  --task-definition inventory-backend-task `
  --desired-count 1 `
  --launch-type FARGATE `
  --network-configuration "awsvpcConfiguration={subnets=[$env:SUBNET_1],securityGroups=[$env:SG_BACKEND_ID],assignPublicIp=ENABLED}" `
  --region $env:REGION
```

## 2-7. バックエンドの Public IP 取得

タスクが RUNNING になるまで 1〜3 分待ってから:

```powershell
$taskArn = (aws ecs list-tasks --cluster inventory-cluster --service-name inventory-backend-service --desired-status RUNNING --query "taskArns[0]" --output text --region $env:REGION)
$eniId = (aws ecs describe-tasks --cluster inventory-cluster --tasks $taskArn --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" --output text --region $env:REGION)
$env:BACKEND_PUBLIC_IP = (aws ec2 describe-network-interfaces --network-interface-ids $eniId --query "NetworkInterfaces[0].Association.PublicIp" --output text --region $env:REGION)
Write-Host "Backend URL: http://${env:BACKEND_PUBLIC_IP}:8000"
```

ブラウザで `http://<BACKEND_PUBLIC_IP>:8000/health` などにアクセスして応答があれば OK。  
**この IP をメモする**（次の Step 3 でフロントの API 向き先に使う）。

---

# Step 3: フロントの API 向き先をバックエンドにする

フロントは **実行時** に環境変数 `VITE_API_URL` を読むため、**タスク定義にこの環境変数を追加** すればよく、イメージの再ビルドは不要です。

## 3-1. フロント用タスク定義の新しいリビジョン（コンソール）

1. **ECS** → **タスク定義** → **inventory-task** → **新しいリビジョンの作成**。
2. **コンテナ** → **app** を展開し、**環境変数** に 1 件追加:
   - キー: `VITE_API_URL`
   - 値: `http://<Step 2-7 で取得したバックエンドの Public IP>:8000`（例: `http://54.123.45.67:8000`）
3. **作成** で新しいリビジョン（例: 2）ができる。

## 3-2. フロントサービスを新リビジョンで再デプロイ

```powershell
# 最新リビジョンを明示する場合（例: 2）
aws ecs update-service --cluster inventory-cluster --service inventory-service --task-definition inventory-task:2 --force-new-deployment --region $env:REGION

# 常に「最新」を使う場合はリビジョン番号なしでも可
aws ecs update-service --cluster inventory-cluster --service inventory-service --task-definition inventory-task --force-new-deployment --region $env:REGION
```

タスクが 1 つ RUNNING に戻るまで待つ。**フロントの Public IP は通常そのまま**（タスクの差し替えのみ）。

---

# Step 4: 動作確認

1. フロントの URL を開く（従来どおり `http://<フロントの Public IP>:5173`。フロントの IP は変わっていない想定）。
2. ログイン画面で **admin / admin** でログインできることを確認。

**うまくいかない場合**

- ログインできない: ブラウザの開発者ツールでネットワークを確認。`/auth/login` がバックエンドの IP:8000 に向いているか。CORS エラーなら、タスク定義の `cors_origins` に `http://<フロントの IP>:5173` が含まれているか確認。
- バックエンドが 500: CloudWatch Logs の `/ecs/inventory-backend-task` で RDS 接続エラーやマイグレーション失敗がないか確認。
- バックエンドのタスクが再作成されると **Public IP が変わる** ため、そのたびに (1) バックエンドの新しい IP を取得し、(2) フロントのタスク定義の `VITE_API_URL` をその IP に更新して新しいリビジョンを作成、(3) フロントサービスをそのリビジョンで再デプロイする必要があります。固定 URL にしたい場合は ALB をバックエンドの前に置く構成にしてください。

---

# 運用: バックエンドの IP が変わったときのやり直し

バックエンドのタスクが再起動されると Public IP が変わり、フロントからログインできなくなります。そのときは次の手順で **フロントの API 向き先だけ** やり直します。

## 変数を用意（PowerShell）

```powershell
$env:REGION = "ap-northeast-1"
```

## 手順 1: バックエンドの新しい Public IP を取得

```powershell
$taskArn = (aws ecs list-tasks --cluster inventory-cluster --service-name inventory-backend-service --desired-status RUNNING --query "taskArns[0]" --output text --region $env:REGION)
$eniId = (aws ecs describe-tasks --cluster inventory-cluster --tasks $taskArn --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" --output text --region $env:REGION)
$env:BACKEND_PUBLIC_IP = (aws ec2 describe-network-interfaces --network-interface-ids $eniId --query "NetworkInterfaces[0].Association.PublicIp" --output text --region $env:REGION)
Write-Host "新しいバックエンド URL: http://${env:BACKEND_PUBLIC_IP}:8000"
```

表示された IP をメモする（例: `18.183.125.102`）。

## 手順 2: フロントのタスク定義で VITE_API_URL を更新

1. **ECS** → **タスク定義** → **inventory-task** をクリック。
2. **「新しいリビジョンの作成」** をクリック。
3. コンテナ **app** を展開し、**環境変数** の **VITE_API_URL** の値を  
   `http://<手順1で表示されたIP>:8000` に変更（例: `http://18.183.125.102:8000`）。
4. **「作成」** をクリック（新しいリビジョン番号ができる。例: 3）。

## 手順 3: フロントサービスを新リビジョンで再デプロイ

```powershell
# 新しいリビジョン番号に合わせて :3 などを指定
aws ecs update-service --cluster inventory-cluster --service inventory-service --task-definition inventory-task --force-new-deployment --region $env:REGION
```

※ タスク定義を「最新」にしておけばリビジョン番号は省略可。明示する場合の例:

```powershell
aws ecs update-service --cluster inventory-cluster --service inventory-service --task-definition inventory-task:3 --force-new-deployment --region $env:REGION
```

## 手順 4: 確認

1〜2 分待ってから、フロントの URL で再度 **admin / admin** でログインできるか確認する。

---

# まとめ

| リソース | 名前 / 値 |
|----------|------------|
| RDS | インスタンス ID: `inventory-db`、DB 名: `inventory` |
| バックエンド ECR | `inventory-ledger-backend` |
| バックエンドタスク定義 | `inventory-backend-task` |
| バックエンドサービス | `inventory-backend-service` |
| フロント | 既存 `inventory-service` を再デプロイして API 向き先をバックエンドに |

ログイン用の admin ユーザーはバックエンド起動時の `app.seed` で作成されます（admin / admin）。
