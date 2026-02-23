# GitHub へのプッシュ手順（ZAIKO_0223）

プロジェクトフォルダ（在庫管理アプリ）で、**PowerShell または コマンドプロンプト**を開き、順に実行してください。

## 1. フォルダに移動

```powershell
cd "c:\Users\満尾和博\OneDrive\デスクトップ\在庫管理アプリ"
```

（エクスプローラーでこのフォルダを開き、アドレス欄に `cmd` と入力して Enter すると、このフォルダでコマンドが開きます。）

## 2. Git を初期化（まだの場合）

```powershell
git init
```

## 3. リモートを追加

```powershell
git remote add origin https://github.com/MITSUO1206/ZAIKO_0223.git
```

すでに `origin` がある場合は、次のように上書きします。

```powershell
git remote set-url origin https://github.com/MITSUO1206/ZAIKO_0223.git
```

## 4. ファイルを追加してコミット

```powershell
git add .
git status
```

（`.env` は .gitignore に入っているので含まれません。問題なければ）

```powershell
git commit -m "Initial commit: 在庫管理アプリ"
```

## 5. ブランチ名を main にしてプッシュ

```powershell
git branch -M main
git push -u origin main
```

---

**認証**: プッシュ時に GitHub のユーザー名・パスワードを聞かれた場合、パスワードには **Personal Access Token (PAT)** を使います。  
GitHub → Settings → Developer settings → Personal access tokens でトークンを作成し、そのトークンをパスワード欄に入力してください。
