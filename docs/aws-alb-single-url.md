# ALB で 1 つの URL にまとめてデプロイする

フロントとバックエンドを **Application Load Balancer (ALB)** の前でまとめ、**1 つの URL**（例: `http://inventory-xxx.ap-northeast-1.elb.amazonaws.com`）でアクセスできるようにする手順です。

- **パス振り分け**: `/*` → フロント（5173）、`/api/*` → バックエンド（8000）
- フロントは **VITE_API_URL を未設定** にし、相対パス `/api` で API を呼ぶ（同一オリジン）
- バックエンドは **`/api` プレフィックス付き** でも応答するようコード対応済み

**前提**: `aws-fargate-backend-db.md` まで完了し、RDS・バックエンド・フロントが Fargate で動いていること。ALB を追加し、両サービスを ALB のターゲットグループに登録します。

---

## 変数（PowerShell）

```powershell
$env:AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
$env:REGION = "ap-northeast-1"
$env:VPC_ID = (aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text --region $env:REGION)
$env:SUBNET_IDS = (aws ec2 describe-subnets --filters "Name=vpc-id,Values=$env:VPC_ID" --query "Subnets[*].SubnetId" --output text --region $env:REGION) -replace '\s+', ','
# サブネットを 2 つ（ALB 用）
$env:SUBNET_1 = ($env:SUBNET_IDS -split ',')[0]
$env:SUBNET_2 = ($env:SUBNET_IDS -split ',')[1]
```

---

# Step 1: ALB 用セキュリティグループ

```powershell
$env:SG_ALB_NAME = "inventory-alb-sg"
$env:SG_ALB_ID = (aws ec2 create-security-group `
  --group-name $env:SG_ALB_NAME `
  --description "ALB for inventory app" `
  --vpc-id $env:VPC_ID `
  --region $env:REGION `
  --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id $env:SG_ALB_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $env:REGION
Write-Host "SG_ALB_ID=$env:SG_ALB_ID"
```

---

# Step 2: ターゲットグループ（フロント・バックエンド）

```powershell
# フロント用（ポート 5173）
$env:TG_FRONTEND_NAME = "inventory-frontend-tg"
$env:TG_FRONTEND_ARN = (aws elbv2 create-target-group `
  --name $env:TG_FRONTEND_NAME `
  --protocol HTTP `
  --port 5173 `
  --vpc-id $env:VPC_ID `
  --target-type ip `
  --health-check-path "/" `
  --health-check-interval-seconds 30 `
  --region $env:REGION `
  --query "TargetGroups[0].TargetGroupArn" --output text)

# バックエンド用（ポート 8000、ヘルスチェックは /api/health）
$env:TG_BACKEND_NAME = "inventory-backend-tg"
$env:TG_BACKEND_ARN = (aws elbv2 create-target-group `
  --name $env:TG_BACKEND_NAME `
  --protocol HTTP `
  --port 8000 `
  --vpc-id $env:VPC_ID `
  --target-type ip `
  --health-check-path "/health" `
  --health-check-interval-seconds 30 `
  --region $env:REGION `
  --query "TargetGroups[0].TargetGroupArn" --output text)

Write-Host "TG_FRONTEND_ARN=$env:TG_FRONTEND_ARN"
Write-Host "TG_BACKEND_ARN=$env:TG_BACKEND_ARN"
```

---

# Step 3: ALB 作成とリスナー（パスルール）

```powershell
$env:ALB_NAME = "inventory-alb"
$env:ALB_ARN = (aws elbv2 create-load-balancer `
  --name $env:ALB_NAME `
  --subnets $env:SUBNET_1 $env:SUBNET_2 `
  --security-groups $env:SG_ALB_ID `
  --scheme internet-facing `
  --type application `
  --region $env:REGION `
  --query "LoadBalancers[0].LoadBalancerArn" --output text)

# リスナー（デフォルト: フロント）
$env:LISTENER_ARN = (aws elbv2 create-listener `
  --load-balancer-arn $env:ALB_ARN `
  --protocol HTTP `
  --port 80 `
  --default-actions "Type=forward,TargetGroupArn=$env:TG_FRONTEND_ARN" `
  --region $env:REGION `
  --query "Listeners[0].ListenerArn" --output text)
```

**パスルール追加**: `/api/*` をバックエンドへ。

変数が消えている・名前で見つからない場合は、**コンソールで ARN をコピー**するか、下の「ARN を 1 つずつ取得」を実行する。

```powershell
# ARN を 1 つずつ取得（リージョンは ap-northeast-1）
# 1) ALB 一覧で inventory を含む ALB の LoadBalancerArn を確認
aws elbv2 describe-load-balancers --region ap-northeast-1 --query "LoadBalancers[*].{Name:LoadBalancerName,Arn:LoadBalancerArn}" --output table

# 2) 上で表示した ALB の ARN を $env:ALB_ARN に代入（例）
# $env:ALB_ARN = "arn:aws:elasticloadbalancing:ap-northeast-1:123456789012:loadbalancer/app/inventory-alb/xxxxx"

# 3) その ALB のリスナー ARN を取得
aws elbv2 describe-listeners --load-balancer-arn $env:ALB_ARN --region ap-northeast-1 --query "Listeners[0].ListenerArn" --output text
# 表示された ARN を $env:LISTENER_ARN に代入

# 4) ターゲットグループ一覧で backend を含む TG の TargetGroupArn を確認
aws elbv2 describe-target-groups --region ap-northeast-1 --query "TargetGroups[*].{Name:TargetGroupName,Arn:TargetGroupArn}" --output table
# バックエンド用の ARN を $env:TG_BACKEND_ARN に代入

# 5) ルール作成
aws elbv2 create-rule --listener-arn $env:LISTENER_ARN --priority 10 --conditions "Field=path-pattern,Values='/api/*'" --actions "Type=forward,TargetGroupArn=$env:TG_BACKEND_ARN" --region ap-northeast-1
```

**ALB の DNS 名を取得**（これが 1 つの URL になります）:

```powershell
$env:ALB_DNS = (aws elbv2 describe-load-balancers --load-balancer-arns $env:ALB_ARN --query "LoadBalancers[0].DNSName" --output text --region $env:REGION)
Write-Host "アプリの URL: http://${env:ALB_DNS}"
```

---

# Step 4: タスクの SG で ALB からのアクセスを許可

既存のフロント・バックエンド用 SG に「ALB からのインバウンド」を追加します。SG 名は環境により異なるため、サービスで使っている SG を確認してから追加してください。

```powershell
# フロントサービスで使っている SG（例: ecs-fargate-sg-inventory-service）
$env:SG_FRONTEND_ID = (aws ecs describe-services --cluster inventory-cluster --services inventory-service --query "services[0].networkConfiguration.awsvpcConfiguration.securityGroups[0]" --output text --region $env:REGION)
# バックエンド用 SG（例: ecs-backend-inventory）
$env:SG_BACKEND_ID = (aws ecs describe-services --cluster inventory-cluster --services inventory-backend-service --query "services[0].networkConfiguration.awsvpcConfiguration.securityGroups[0]" --output text --region $env:REGION)

# ALB からフロント 5173 を許可
aws ec2 authorize-security-group-ingress --group-id $env:SG_FRONTEND_ID --protocol tcp --port 5173 --source-group $env:SG_ALB_ID --region $env:REGION

# ALB からバックエンド 8000 を許可
aws ec2 authorize-security-group-ingress --group-id $env:SG_BACKEND_ID --protocol tcp --port 8000 --source-group $env:SG_ALB_ID --region $env:REGION
```

既に同じルールがある場合はエラーでよい（スキップ）。

---

# Step 5: ECS サービスを ALB のターゲットグループに登録

フロント・バックエンドの**両方**のサービスに、それぞれのターゲットグループを紐付けます。

```powershell
# フロント: ターゲットグループとコンテナ名・ポートを指定
aws ecs update-service `
  --cluster inventory-cluster `
  --service inventory-service `
  --load-balancers "targetGroupArn=$env:TG_FRONTEND_ARN,containerName=app,containerPort=5173" `
  --force-new-deployment `
  --region $env:REGION

# バックエンド
aws ecs update-service `
  --cluster inventory-cluster `
  --service inventory-backend-service `
  --load-balancers "targetGroupArn=$env:TG_BACKEND_ARN,containerName=backend,containerPort=8000" `
  --force-new-deployment `
  --region $env:REGION
```

**注意**: `--load-balancers` を付けると、既存の `networkConfiguration` はそのままですが、**assignPublicIp** は不要になります。タスクは ALB 経由で届くため、パブリック IP がなくても問題ありません。サブネットはそのまま（パブリックサブネットで可）でよいです。

タスクが RUNNING になり、ターゲットグループの「ターゲット」が healthy になるまで **2〜5 分** かかることがあります。

---

# Step 6: フロントのタスク定義（VITE_API_URL を外す）

**1 つの URL** にするため、フロントは **同じオリジンの `/api`** に API を投げます。環境変数 **VITE_API_URL を削除**（または空）にしてください。

1. **ECS** → **タスク定義** → **inventory-task** → **新しいリビジョンの作成**
2. コンテナ **app** の **環境変数** から **VITE_API_URL** を**削除**する（または値は空のまま）
3. **作成** して新しいリビジョン（例: 5）を作成
4. フロントサービスをそのリビジョンで更新:

```powershell
aws ecs update-service --cluster inventory-cluster --service inventory-service --task-definition inventory-task:5 --force-new-deployment --region $env:REGION
```

（リビジョン番号は実際に作成した番号に合わせる）

---

# Step 7: バックエンドの CORS とイメージの更新

- **CORS**: ブラウザのオリジンは ALB の URL になるため、バックエンドのタスク定義の **cors_origins** に `http://<ALB_DNS>` を追加（既に `*` や localhost だけなら、`http://${env:ALB_DNS}` を追加）。
- **コード**: バックエンドは既に `/api` プレフィックス付きで応答するよう変更済み。**イメージを再ビルドして ECR に push** し、バックエンドサービスを再デプロイしてください。

```powershell
# プロジェクトルートで
docker build -t inventory-ledger-backend:latest -f backend/Dockerfile ./backend
$uri = "$($env:AWS_ACCOUNT_ID).dkr.ecr.$($env:REGION).amazonaws.com/inventory-ledger-backend:latest"
docker tag inventory-ledger-backend:latest $uri
docker push $uri
aws ecs update-service --cluster inventory-cluster --service inventory-backend-service --force-new-deployment --region $env:REGION
```

バックエンドのタスク定義で **cors_origins** に ALB の URL（例: `http://inventory-alb-xxxxx.ap-northeast-1.elb.amazonaws.com`）を入れておくと安全です。コンソールで **inventory-backend-task** の新しいリビジョンを作成し、`cors_origins` に上記 URL を追加してからサービスをそのリビジョンで更新してください。

---

# Step 8: 動作確認

1. ブラウザで **http://<ALB_DNS>** を開く（Step 3 で表示した URL）。
2. ログイン画面で **admin / admin** でログインできることを確認。

**うまくいかない場合**

- 503 / 接続できない: ターゲットグループの「ターゲット」が healthy か確認。タスクが RUNNING でも、ヘルスチェックが通るまで 1〜2 分かかることがあります。
- ログインできない: バックエンドのログ（`/ecs/inventory-backend-task`）で `/api/auth/login` が届いているか確認。CORS エラーなら、バックエンドの **cors_origins** に ALB の URL を追加。

---

# HTTPS 化（オプション）

**前提**: HTTPS 用の証明書は **自分で管理するドメイン** にしか発行できません。  
ALB の DNS 名（`*.elb.amazonaws.com`）向けの証明書は発行できないため、**取得済みのドメイン**（例: `app.example.com`）が必要です。

## 手順の流れ

1. **ドメインを用意する**  
   - Route 53 で取得するか、お名前.com などで取得したドメインの DNS を Route 53 に委任する。
2. **ACM で証明書を発行する**（リージョン: **ap-northeast-1**）
3. **ALB に 443 リスナーを追加**し、その証明書を紐付ける。
4. **必要なら HTTP(80) → HTTPS(443) リダイレクト** を設定する。
5. **バックエンドの cors_origins** に `https://<あなたのドメイン>` を追加する。

---

## Step H-1: ドメインと Route 53

- まだドメインがない場合: **Route 53** → ドメインの登録、または **お名前.com** 等で取得後、**ホストゾーン** を作成し、デリゲート設定を行う。
- 例: `inventory.example.com` のように「アプリ用サブドメイン」を 1 つ決める。

---

## Step H-2: ACM で証明書をリクエスト

1. **AWS コンソール** → **Certificate Manager (ACM)** → リージョン **東京 (ap-northeast-1)**。
2. **証明書のリクエスト**。
3. **パブリック証明書** を選択。
4. **ドメイン名**: 使う FQDN を入力（例: `inventory.example.com`）。ワイルドカードなら `*.example.com`。
5. **検証方法**: **DNS 検証** を選択（推奨）。
6. リクエスト後、ACM が表示する **CNAME レコード** を **Route 53 のホストゾーン** に追加する（「Route 53 でレコードを作成」ボタンで自動作成可）。
7. ステータスが **「発行済み」** になるまで待つ（数分〜最大 30 分程度）。

発行済み証明書の **ARN** をメモする（次のステップで使う）。

---

## Step H-3: ALB に HTTPS リスナーを追加

**コンソールの場合**

1. **EC2** → **ロードバランサー** → **inventory-alb** → **リスナー** タブ。
2. **リスナーの追加**。
   - **プロトコル: ポート**: **HTTPS : 443**。
   - **デフォルトアクション**: **フロント用ターゲットグループへ転送**（既存のフロント TG を選択）。
   - **セキュリティポリシー**: デフォルトのままで可。
   - **証明書**: **ACM から証明書を選択** で、Step H-2 で発行した証明書を選ぶ。
3. **保存**。

**CLI の例**（証明書 ARN とフロント TG ARN を自分の値に置き換え）

```powershell
$env:REGION = "ap-northeast-1"
$env:ALB_ARN = (aws elbv2 describe-load-balancers --names inventory-alb --query "LoadBalancers[0].LoadBalancerArn" --output text --region $env:REGION)
$env:TG_FRONTEND_ARN = (aws elbv2 describe-target-groups --names inventory-frontend-tg --query "TargetGroups[0].TargetGroupArn" --output text --region $env:REGION)
$env:CERT_ARN = "arn:aws:acm:ap-northeast-1:119793031484:certificate/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"   # ACM の証明書 ARN に置き換え

aws elbv2 create-listener `
  --load-balancer-arn $env:ALB_ARN `
  --protocol HTTPS `
  --port 443 `
  --certificates CertificateArn=$env:CERT_ARN `
  --default-actions Type=forward,TargetGroupArn=$env:TG_FRONTEND_ARN `
  --region $env:REGION
```

**パスルール**（/api/* をバックエンドへ）は、既存の 80 リスナーと同様に、**443 リスナーにも追加**する必要があります。  
コンソールなら **リスナー** → **443** → **ルールを表示/編集** → **ルールの追加** で、条件「パスは /api/*」、アクション「バックエンド TG へ転送」を設定。

---

## Step H-4: HTTP を HTTPS にリダイレクト（任意）

80 で来たアクセスを 443 に飛ばしたい場合:

1. **ALB** → **リスナー** → **80** の **編集**。
2. **アクション** を **「リダイレクト」** に変更。
   - **プロトコル**: HTTPS
   - **ポート**: 443
   - **ホスト**: 元のホスト（デフォルトのまま）
   - **パス**: 元のパス（デフォルトのまま）
   - **クエリ**: 元のクエリ（デフォルトのまま）
   - **ステータスコード**: 301 または 302
3. **保存**。

---

## Step H-5: ドメインを ALB に向ける

**Route 53** のホストゾーンで、使う FQDN（例: `inventory.example.com`）の **A レコード** を追加する。

- **レコード名**: `inventory`（または使うサブドメイン）
- **レコードタイプ**: **A**
- **エイリアス**: **はい**
- **トラフィックのルーティング先**: **Application Load Balancer へのエイリアス**
- **リージョン**: ap-northeast-1
- **ロードバランサー**: **inventory-alb** を選択

これで `https://inventory.example.com` で ALB（HTTPS）にアクセスできます。

---

## Step H-6: バックエンドの CORS

HTTPS の URL を許可するため、バックエンドのタスク定義の環境変数 **cors_origins** に、  
`https://inventory.example.com`（または実際に使う FQDN）を追加する。  
新しいリビジョンを作成し、フロント／バックエンドの再デプロイが必要なら行う。

---

# まとめ

| 役割 | 内容 |
|------|------|
| 1 つの URL | `http://<ALB の DNS 名>`（HTTPS 化時は `https://<あなたのドメイン>`） |
| パス | `/`・`/login` など → フロント（5173）、`/api/*` → バックエンド（8000） |
| フロント | VITE_API_URL なし → 相対 `/api` で API 呼び出し |
| バックエンド | `/api` プレフィックス付きでルートを二重登録済み（ローカルは従来どおり） |
