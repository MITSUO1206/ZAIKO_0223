# ECS タスク定義登録（JSON をファイルに書き 8.3 パスで AWS CLI に渡す）
# 実行前に 2-1 の変数が設定されていること。プロジェクトルートで: .\scripts\register-ecs-task.ps1

if (-not $env:ECR_URI) {
  $env:ECR_URI = "$($env:AWS_ACCOUNT_ID).dkr.ecr.$($env:REGION).amazonaws.com/$($env:REPO_NAME):latest"
}

$json = @"
{
  "family": "$env:TASK_FAMILY",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "$env:CPU",
  "memory": "$env:MEMORY",
  "executionRoleArn": "arn:aws:iam::$($env:AWS_ACCOUNT_ID):role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "$env:CONTAINER_NAME",
      "image": "$env:ECR_URI",
      "portMappings": [
        {
          "containerPort": $env:APP_PORT,
          "hostPort": $env:APP_PORT,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$env:TASK_FAMILY",
          "awslogs-region": "$env:REGION"
        }
      }
    }
  ]
}
"@

# スクリプトと同じフォルダに task-def.json を保存（ASCII）
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$outPath = Join-Path $scriptDir "task-def.json"
$json | Set-Content -Path $outPath -Encoding ASCII -NoNewline

# 8.3 短いパスを取得（日本語パス対策）
$fso = New-Object -ComObject Scripting.FileSystemObject
$shortPath = $fso.GetFile((Resolve-Path $outPath).Path).ShortPath
$fileUri = "file:///" + $shortPath.Replace('\', '/')

Write-Host "Using: $fileUri"
aws ecs register-task-definition --cli-input-json $fileUri --region $env:REGION
