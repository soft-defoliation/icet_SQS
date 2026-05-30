# 上传项目到 GitHub 指南

## 首次上传

### 1. 在 GitHub 上创建仓库

登录 GitHub → 右上角 `+` → `New repository` → 填仓库名（如 `icet_SQS`）→ Create repository。

**不要**勾选 "Initialize with README"（本地已有代码就不用初始化）。

### 2. 生成 Personal Access Token

GitHub 已于 2021 年 8 月废除密码认证，必须使用 token。

1. 登录 GitHub → Settings → Developer settings → Personal access tokens → **Tokens (classic)**
2. 点击 **Generate new token (classic)**
3. Note 随便填（如 `push-code`）
4. **勾选 `repo`**（第一个大选项，包含完整仓库读写权限）
5. 点击 Generate token
6. **复制 token**（只显示一次）

> ⚠️ 推荐用 Classic Token 而非 Fine-grained Token，权限配置更简单不容易出错。

### 3. 在服务器上操作

```bash
# 进入项目目录
cd /你的项目路径

# 初始化 git
git init
git branch -m main

# 设置身份（填你自己的信息）
git config user.email "你的邮箱"
git config user.name "你的用户名"

# 添加文件并提交
git add .
git commit -m "feat: 项目描述"

# 设置远程仓库（把 你的token 和 仓库名 替换）
git remote set-url origin https://你的用户名:你的token@github.com/你的用户名/仓库名.git

# 推送
git push -u origin main
```

### 4. 需要代理的服务器

如果服务器无法直接访问 GitHub，需要先配代理：

```bash
# 检查是否能访问 GitHub
curl -s -o /dev/null -w "%{http_code}" https://github.com

# 如果超时，查找服务器上的代理
ss -tln | grep -E ':(1080|2019|7890|8080|8888)'
ps aux | grep -i -E '(xray|clash|v2ray)'

# 设置代理（以 xray socks5 端口 2019 为例）
export https_proxy=socks5://127.0.0.1:2019
export http_proxy=socks5://127.0.0.1:2019

# 推送时指定代理
git -c http.proxy=socks5://127.0.0.1:2019 push -u origin main
```

### 5. 推送成功后

**立即删除 token**：GitHub → Settings → Developer settings → Personal access tokens → 删除刚生成的 token。

---

## 日常更新

```bash
cd /你的项目路径
git add .
git commit -m "描述你改了什么"
git -c http.proxy=socks5://127.0.0.1:2019 push
```

## 在新电脑上使用

```bash
git clone https://github.com/你的用户名/仓库名.git
cd 仓库名
pip install -e .
sqskit
```

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `Connection timed out` | 网络不通 | 配代理 |
| `403 Permission denied` | token 权限不够 | 重新生成，确保勾选 `repo` |
| `403 denied to 其他用户` | token 和仓库不属于同一账号 | 用仓库所属账号生成 token |
| `Author identity unknown` | 没配置 git 身份 | `git config user.email/name` |
| `src refspec main does not match` | 默认分支是 master | `git branch -m main` |
| `failed to push some refs` | 远程有新提交 | 先 `git pull --rebase` 再 push |
