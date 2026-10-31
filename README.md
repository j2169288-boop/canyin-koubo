# 餐饮口播助手（手机优先 MVP）

给餐饮老板用的口播工具：**手机浏览器 / PWA** 为主，Streamlit 桌面版仍保留。

- 移动端：Flask + Waitress（端口 **8600**）+ 纯 HTML/CSS/JS（无 CDN）
- 桌面版：Streamlit（端口 **8501**，可选）
- 功能：店铺信息与拍照上传、多风格口播、≤15s 分段、Grok Imagine 视频提示词、抖音投流粗估、JSON 存档、Markdown 导出、PWA、简单密码登录

## 手机访问（推荐）

本地（同一网络 / 本机浏览器）：

```text
http://127.0.0.1:8600
```

登录密码存在文件（权限 600，**不要提交到 git**）：

```text
/workspace/canyin-koubo/.app_password
```

也可通过环境变量 `APP_PASSWORD` 覆盖。

### 启动 / 停止（移动端）

```bash
cd /workspace/canyin-koubo
./scripts/start_mobile.sh    # Waitress :8600
./scripts/stop_mobile.sh     # 停应用与隧道
```

日志：`mobile.log`

### 临时公网链接（cloudflared）

```bash
./scripts/start_tunnel.sh
# 从输出或 cloudflared.log 复制 https://xxxx.trycloudflare.com
```

**已知限制（当前云电脑环境）：** 出口代理可能导致 `cloudflared` 无法完成与 Cloudflare 边缘的 TLS 握手（日志常见 `TLS handshake with edge error: EOF`，公网访问返回 **530**）。本地 `http://127.0.0.1:8600` 正常。备选：在你自己的电脑/手机热点同网打开，或等网络允许后再跑 `start_tunnel.sh`；也可用 ngrok（需自备 token）。

临时链接每次重启会变；云电脑关机后无法访问。

### 改密码

```bash
# 写入新密码（仅小写字母+数字更易手机输入）
python3 - <<'PY'
from pathlib import Path
p = Path('/workspace/canyin-koubo/.app_password')
p.write_text('你的新密码\n', encoding='utf-8')
p.chmod(0o600)
print('updated', p)
PY
# 或: export APP_PASSWORD='你的新密码' 后重启 start_mobile.sh
```

### 添加到手机桌面（PWA）

Safari / Chrome → 分享 / 菜单 → **添加到主屏幕**。已提供 `manifest.json`、Service Worker、192/512 与 apple-touch-icon。


## Render 部署（免费 Web Service）

适合把手机版挂到公网，商家用手机浏览器打开。**不要把 `.app_password` 提交到仓库**；在 Render 控制台设置环境变量。

### 1. 推到 GitHub

在本机（或你自己的电脑）把本仓库推到 GitHub（首次若尚未 `git remote`）：

```bash
cd /workspace/canyin-koubo   # 或你 clone 后的路径
git status                   # 确认 .app_password 未被跟踪
# 创建空仓库后：
# git remote add origin https://github.com/<你>/<仓库>.git
# git push -u origin main
```

### 2. 用 Blueprint 或 New Web Service

**方式 A — Blueprint（推荐）**  
Render Dashboard → **New** → **Blueprint** → 连接该 GitHub 仓库 → 使用根目录 `render.yaml`。  
部署前在环境变量里填入 **APP_PASSWORD**（`SECRET_KEY` 已 `generateValue` 自动生成）。可选填 `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL`。

**方式 B — New Web Service**  
- Runtime: Python  
- Build: `pip install -r requirements.txt`  
- Start: `gunicorn server:app --bind 0.0.0.0:$PORT`  
- Plan: Free  
- 环境变量同上（必填 `APP_PASSWORD`，建议让 Render 生成 `SECRET_KEY`）

主 `requirements.txt` **仅含 Flask + gunicorn**；Streamlit 等本地依赖在 `requirements-streamlit.txt`，**不要**在 Render 安装。

### 3. 免费版注意

- **休眠**：一段时间无访问后服务会睡；下次打开可能要等几十秒冷启动。  
- **磁盘不持久**：免费实例文件系统会丢；店铺 JSON / 上传照片重启后可能消失。需要持久化时可自备外部存储，或设置 `DATA_DIR` 指向挂载盘（付费磁盘）。  
- **无默认密码**：未设置 `APP_PASSWORD` 时生产环境**拒绝启动**。  
- HTTPS 下 Cookie 为 Secure；用手机访问 Render 域名即可，也可「添加到主屏幕」当 PWA。

### 4. 部署后自检

打开 `https://<你的服务>.onrender.com/login` → 用你设的 `APP_PASSWORD` 登录 → 填入示例「老王烧烤」→ 生成口播。

## Streamlit 旧版（保留）

```bash
cd /workspace/canyin-koubo && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-streamlit.txt
streamlit run app.py --server.port 8501 --server.headless true
```

## 可选 LLM

```bash
export OPENAI_API_KEY=...          # 或 XAI_API_KEY
export OPENAI_BASE_URL=https://api.x.ai/v1
export OPENAI_MODEL=grok-2-latest
```

不配则用内置模板；失败自动回退。

## 目录

```
canyin-koubo/
  server.py              # Flask API + 静态页
  app.py                 # Streamlit（旧）
  web/                   # 移动端前端 / PWA
  lib/                   # 生成 / 分段 / prompt / 投流 / 店铺 JSON
  scripts/start_mobile.sh
  scripts/stop_mobile.sh
  scripts/start_tunnel.sh
  scripts/test_core.py
  data/stores/
  screenshots/           # 390×844 手机截图
  .app_password          # 访问密码（600）
```

## API 摘要（均需登录 Cookie）

- `POST /api/login` `{password}`
- `GET/POST /api/stores`、`GET /api/stores/<name>`、`POST .../photos`
- `POST /api/generate`、`/api/segment`、`/api/prompts`、`/api/ad-estimate`
- `POST /api/export/markdown`、`GET /api/example`

未登录访问 API → **401**。

## 免责声明

投流数字为「行业经验参考假设」，**仅供参考，不构成收益保证**。示例「老王烧烤」为演示数据。
