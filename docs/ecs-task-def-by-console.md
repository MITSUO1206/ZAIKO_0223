# タスク定義をコンソールで作成する（Windows で file パスが通らない場合）

PowerShell からはタスク定義の JSON を渡せないため、**AWS マネジメントコンソールで 1 回だけ**タスク定義を作成してください。作成後は CLI の `create-service` でそのまま使えます。

---

## 1. 自分のアカウント ID を確認

PowerShell で:

```powershell
aws sts get-caller-identity --query Account --output text
```

表示された 12 桁の数字（例: `119793031484`）をメモする。

---

## 2. ロググループを先に作る（CLI）

```powershell
aws logs create-log-group --log-group-name "/ecs/inventory-task" --region ap-northeast-1
```

既にある場合はエラーでよい。

---

## 3. ECS でタスク定義を新規作成

1. **AWS マネジメントコンソール** → **ECS** → リージョン **東京 (ap-northeast-1)** に合わせる。
2. 左メニュー **「タスク定義」** → **「新しいタスク定義の作成」**。
3. **「JSON タブ」** を開く。
4. いったん表示されている内容を **すべて削除** し、下の JSON を **そのまま貼り付け** する。
5. 貼り付けた JSON の **`YOUR_ACCOUNT_ID`** を、手順 1 でメモした **12 桁のアカウント ID** に置き換える（2 箇所: executionRoleArn と image）。
6. **「作成」** をクリック。

### 貼り付ける JSON（YOUR_ACCOUNT_ID を置き換える）

```json
{
  "family": "inventory-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.ap-northeast-1.amazonaws.com/inventory-ledger-app:latest",
      "portMappings": [
        {
          "containerPort": 5173,
          "hostPort": 5173,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/inventory-task",
          "awslogs-region": "ap-northeast-1"
        }
      }
    }
  ]
}
```

**置き換え例:** アカウント ID が `119793031484` の場合  
- `YOUR_ACCOUNT_ID` → `119793031484`（3 箇所）  
- `image` は `119793031484.dkr.ecr.ap-northeast-1.amazonaws.com/inventory-ledger-app:latest` になる。

---

## 4. 作成できたか確認

ECS → タスク定義 → **inventory-task** が表示され、ステータスが **「アクティブ」** であれば OK。

---

## 5. サービス作成（PowerShell）

変数がまだなら 2-1 を再実行してから、以下を実行:

```powershell
aws ecs create-service `
  --cluster $env:CLUSTER_NAME `
  --service-name $env:SERVICE_NAME `
  --task-definition inventory-task `
  --desired-count 1 `
  --launch-type FARGATE `
  --network-configuration "awsvpcConfiguration={subnets=[$env:SUBNET_1],securityGroups=[$env:SG_ID],assignPublicIp=ENABLED}" `
  --region $env:REGION
```

あとはタスクが RUNNING になったら、2-7 のコマンドで Public IP を取得してブラウザで開く。
