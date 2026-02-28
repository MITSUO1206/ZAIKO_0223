# AWS ECS (Fargate) 最短デプロイ手順

リージョン: **ap-northeast-1（東京）**  
方式: **ALB なし・タスクに Public IP 割当**でブラウザから動作確認。

---

## 前提・準備

- AWS CLI が入っていること: `aws --version`
- AWS の認証済みであること: `aws sts get-caller-identity` でアカウントID等が返ること
- 未設定なら: `aws configure` で Access Key / Secret / リージョン `ap-northeast-1` を設定

---

## 変数（冒頭で設定して以降使い回す）

```bash
# === 必ず自分の環境に合わせて書き換える ===
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export REGION=ap-northeast-1
export REPO_NAME=inventory-ledger-app          # ECR リポジトリ名（任意）
export CLUSTER_NAME=inventory-cluster
export SERVICE_NAME=inventory-service
export TASK_FAMILY=inventory-task
export APP_PORT=5173                            # アプリの待ち受けポート（Vite=5173, FastAPI=8000 等）
export CONTAINER_NAME=app
export CPU=256
export MEMORY=512
```

---

# Step1: ECR 作成とイメージ push

## 1-1. ECR リポジトリ作成

```bash
aws ecr create-repository \
  --repository-name "$REPO_NAME" \
  --region "$REGION" \
  --image-scanning-configuration scanOnPush=true
```

**確認**: マネジメントコンソール → ECR → リポジトリに `$REPO_NAME` が表示される。

## 1-2. ECR にログイン

```bash
aws ecr get-login-password --region "$REGION" | \
  docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
```

**確認**: `Login Succeeded` と出れば OK。

## 1-3. イメージのビルド・タグ・push（フロントのみの例）

**※ プロジェクトルートで、Dockerfile があるディレクトリで実行。**

```bash
# 例: frontend 用 Dockerfile がある場合
docker build -t "$REPO_NAME":latest -f frontend/Dockerfile ./frontend

# または 1 コンテナでアプリ全体を動かす Dockerfile がルートにある場合
# docker build -t "$REPO_NAME":latest .
```

```bash
docker tag "$REPO_NAME":latest "$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME":latest
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME":latest
```

**確認**: ECR → リポジトリ → `$REPO_NAME` → タグ `latest` のイメージが 1 つある。

**つまずきポイント**:
- `no basic auth credentials`: 1-2 のログインが切れている。再度 `get-login-password` から実行。
- `denied`: IAM で `ecr:GetDownloadUrlForLayer` 等が付いたポリシーがユーザー/ロールに必要。

---

# Step2: ECS (Fargate) でデプロイ・Public IP でアクセス

## 2-1. デフォルト VPC とパブリックサブネットの確認

```bash
# デフォルト VPC の ID 取得（なければ次の 2-1' で新規作成）
export VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text --region "$REGION")

# デフォルト VPC が無い場合
if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
  echo "Default VPC not found. Create one or use existing VPC."
  # 手動で VPC を作る場合の例（最短）
  # aws ec2 create-vpc --cidr-block 10.0.0.0/16 --region "$REGION" --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=my-vpc}]'
  # その後サブネット・IGW・ルートテーブルを設定
fi
echo "VPC_ID=$VPC_ID"
```

```bash
# パブリックサブネット（Fargate で Public IP を付与するならここを使う）
export SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[*].SubnetId" --output text --region "$REGION" | tr '\t' ',')
echo "SUBNET_IDS=$SUBNET_IDS"
# 2 つ以上ある場合はカンマ区切り。1 つだけ使う場合: SUBNET_IDS=$(aws ec2 describe-subnets ... --query "Subnets[0].SubnetId" --output text)
```

**確認**: `VPC_ID` が `vpc-xxxxx`、`SUBNET_IDS` が `subnet-xxx,subnet-yyy` のように出る。

## 2-2. IAM: ECS タスク実行ロール（ecsTaskExecutionRole）

ECS が ECR からイメージを pull し、CloudWatch Logs に送るために必要。

```bash
# ロールが既にあるか確認
aws iam get-role --role-name ecsTaskExecutionRole 2>/dev/null && echo "Role exists" || true

# 無い場合のみ作成
cat << 'EOF' > /tmp/ecs-trust-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file:///tmp/ecs-trust-policy.json \
  2>/dev/null || echo "Role may already exist, continuing..."

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

**確認**: IAM → ロール → `ecsTaskExecutionRole` が存在し、`AmazonECSTaskExecutionRolePolicy` がアタッチされている。

## 2-3. セキュリティグループ作成（APP_PORT を開放）

```bash
export SG_NAME=ecs-fargate-sg-$SERVICE_NAME
export SG_ID=$(aws ec2 create-security-group \
  --group-name "$SG_NAME" \
  --description "Allow APP_PORT for ECS Fargate verification" \
  --vpc-id "$VPC_ID" \
  --region "$REGION" \
  --query GroupId --output text)
echo "SG_ID=$SG_ID"
```

```bash
# アプリのポートを 0.0.0.0/0 で開放（検証用。本番は ALB のみ等に制限すること）
aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp \
  --port "$APP_PORT" \
  --cidr 0.0.0.0/0 \
  --region "$REGION"
```

**確認**: EC2 → セキュリティグループ → `$SG_NAME` のインバウンドに `TCP / $APP_PORT / 0.0.0.0/0` がある。

## 2-4. ECS クラスター作成

```bash
aws ecs create-cluster \
  --cluster-name "$CLUSTER_NAME" \
  --region "$REGION"
```

**確認**: ECS → クラスター → `$CLUSTER_NAME` が 1 つある。

## 2-5. タスク定義（Fargate・Public IP 用）

イメージ URI とポートを変数で差し替えた JSON を登録する。

```bash
export ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest"

cat << EOF > /tmp/task-def.json
{
  "family": "$TASK_FAMILY",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "$CPU",
  "memory": "$MEMORY",
  "executionRoleArn": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "$CONTAINER_NAME",
      "image": "$ECR_URI",
      "portMappings": [
        {
          "containerPort": $APP_PORT,
          "hostPort": $APP_PORT,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$TASK_FAMILY",
          "awslogs-region": "$REGION"
        }
      }
    }
  ]
}
EOF
```

ログ用の Logs グループを先に作る（ないとタスクが起動しない場合あり）:

```bash
aws logs create-log-group --log-group-name "/ecs/$TASK_FAMILY" --region "$REGION" 2>/dev/null || true
```

タスク定義を登録:

```bash
aws ecs register-task-definition \
  --cli-input-json file:///tmp/task-def.json \
  --region "$REGION"
```

**確認**: ECS → タスク定義 → `$TASK_FAMILY` が「アクティブ」で最新リビジョン（例: 1）がある。

## 2-6. サービス作成（Public IP 付与・1 タスク）

パブリックサブネットを 1 つ以上指定し、`assignPublicIp=ENABLED` にすることが必須。

```bash
# サブネットはカンマ区切りで複数可。ここでは 1 つ目だけ使う例
export SUBNET_1=$(echo "$SUBNET_IDS" | cut -d',' -f1)
```

```bash
aws ecs create-service \
  --cluster "$CLUSTER_NAME" \
  --service-name "$SERVICE_NAME" \
  --task-definition "$TASK_FAMILY" \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
  --region "$REGION"
```

**確認**: ECS → クラスター → サービス → `$SERVICE_NAME` の「実行中のタスク数」が 1 になるまで待つ（1〜3 分程度）。

**つまずきポイント**:
- タスクがすぐ STOP になる: タスクの「停止理由」を確認。よくあるのは「CannotPullContainerError」（ECR のイメージ名/タグ違い、実行ロール不足）、「ResourceInitializationError」（ロググループや実行ロール不足）。

## 2-7. タスクの Public IP を取得してアクセス確認

```bash
export TASK_ARN=$(aws ecs list-tasks --cluster "$CLUSTER_NAME" --service-name "$SERVICE_NAME" --desired-status RUNNING --query "taskArns[0]" --output text --region "$REGION")
export ENI_ID=$(aws ecs describe-tasks --cluster "$CLUSTER_NAME" --tasks "$TASK_ARN" --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" --output text --region "$REGION")
export PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids "$ENI_ID" --query "NetworkInterfaces[0].Association.PublicIp" --output text --region "$REGION")
echo "Open in browser: http://$PUBLIC_IP:$APP_PORT"
```

**確認**: ブラウザで `http://<PUBLIC_IP>:<APP_PORT>` を開き、アプリが表示される。

**つまずきポイント**:
- 接続できない: セキュリティグループで `$APP_PORT` が 0.0.0.0/0 で開いているか、タスクが「RUNNING」か再確認。
- コンテナ内で別ポートで待ち受けている場合は、`containerPort` / `hostPort` と `APP_PORT` をそのポートに合わせる。

---

# Step3: GitHub Actions で push → ECR → ECS 更新

## 3-1. 必要な IAM（GitHub 用）

**方式 A: アクセスキー（検証向け・最短）**

- IAM ユーザーを作成し、以下のインラインポリシー（またはカスタムポリシー）を付与。
- アクセスキーを発行し、GitHub リポジトリの「Settings → Secrets and variables → Actions」に以下を登録:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`

**推奨ポリシー（ECR push + ECS 更新用）:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "arn:aws:ecr:ap-northeast-1:YOUR_ACCOUNT_ID:repository/YOUR_REPO_NAME"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:UpdateService",
        "ecs:DescribeServices"
      ],
      "Resource": "*"
    }
  ]
}
```

`YOUR_ACCOUNT_ID` / `YOUR_REPO_NAME` は実際の値に置き換える。

## 3-2. GitHub Actions ワークフロー例

リポジトリに `.github/workflows/deploy-ecs.yml` を置く。

```yaml
name: Deploy to ECS Fargate

on:
  push:
    branches: [main]

env:
  AWS_REGION: ap-northeast-1
  ECR_REPO: inventory-ledger-app
  ECS_CLUSTER: inventory-cluster
  ECS_SERVICE: inventory-service
  CONTAINER_NAME: app

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: ECR Login
        id: ecr
        run: |
          aws ecr get-login-password --region $AWS_REGION | \
            docker login --username AWS --password-stdin ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.$AWS_REGION.amazonaws.com
          echo "image=${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest" >> $GITHUB_OUTPUT

      - name: Build and push
        run: |
          docker build -t ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest -f frontend/Dockerfile ./frontend
          docker push ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest
        # ルートの Dockerfile で 1 コンテナの場合は:
        # docker build -t ${{ ... }}:latest .
        # docker push ${{ ... }}:latest

      - name: ECS service update
        run: |
          aws ecs update-service \
            --cluster $ECS_CLUSTER \
            --service $ECS_SERVICE \
            --force-new-deployment \
            --region $AWS_REGION
```

**GitHub Secrets に追加するもの:**

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_ACCOUNT_ID`（12 桁の数字）

**確認**: `main` に push 後、Actions タブでワークフローが成功し、ECS の「デプロイ」が「完了」になる。数分後に再度 `http://<Public IP>:<APP_PORT>` で新しいイメージで動いているか確認。

---

## チェックリスト（つまずきやすい確認ポイント）

| ステップ | 確認場所 | OK の目安 |
|----------|----------|-----------|
| Step1 push | ECR → リポジトリ → タグ | `latest` のイメージが 1 つある |
| Step2 タスク | ECS → クラスター → タスク | ステータス「RUNNING」 |
| Step2 ネット | タスク → ネットワーク | パブリック IP が表示されている |
| Step2 通信 | ブラウザ | `http://<PublicIP>:APP_PORT` でアプリ表示 |
| Step2 落ちる | タスク → 停止したタスク → 停止理由 | ログ・ECR・ロールを確認 |
| Step3 | GitHub Actions | ジョブが緑で完了、ECS デプロイが完了 |

---

## 補足: 複数コンテナ（例: フロント＋API）の場合

- 1 タスクで複数コンテナにする場合は、`task-def.json` の `containerDefinitions` に複数要素を並べ、必要なポートを `portMappings` で開く。
- 別々のタスク（フロント用サービス・API 用サービス）にする場合は、タスク定義とサービスを 2 つ作り、`APP_PORT` やイメージをそれぞれのコンテナ用に変える。

このドキュメントの変数（`REPO_NAME`, `APP_PORT` 等）を自分のプロジェクトに合わせれば、そのままコピペで Step1〜Step3 まで実行できます。
