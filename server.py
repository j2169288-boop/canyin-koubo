"""餐饮口播助手 — 移动端友好 Flask API + 静态前端。"""
from __future__ import annotations

import json
import os
import secrets
import sys
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    request,
    session,
    send_from_directory,
    redirect,
    url_for,
)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lib.ad_estimate import DEFAULT_ASSUMPTIONS, estimate_douyin
from lib.llm import generate_with_llm, llm_configured
from lib.segmenter import segment_script
from lib.store_config import list_stores, load_store, photos_dir, save_store, default_store_template
from lib.templates import STYLES, generate_versions
from lib.video_prompts import build_prompts_for_version, ensure_avatar, DEFAULT_AVATAR

WEB = ROOT / "web"
STATIC = WEB / "static"
TEMPLATES = WEB / "templates"

app = Flask(
    __name__,
    static_folder=str(STATIC),
    static_url_path="/static",
    template_folder=str(TEMPLATES),
)
def _is_production() -> bool:
    """Render / 显式生产环境。"""
    if os.environ.get("RENDER", "").lower() in ("1", "true", "yes"):
        return True
    env = (os.environ.get("FLASK_ENV") or os.environ.get("ENV") or "").lower()
    return env in ("production", "prod")


# Session secret：优先 SECRET_KEY（Render Blueprint），兼容 FLASK_SECRET_KEY；本地无则临时生成
app.secret_key = (
    os.environ.get("SECRET_KEY")
    or os.environ.get("FLASK_SECRET_KEY")
    or (None if _is_production() else secrets.token_hex(32))
)
if not app.secret_key:
    raise SystemExit("生产环境必须设置 SECRET_KEY（或 FLASK_SECRET_KEY）")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# HTTPS 部署（Render）默认 Secure Cookie；可用 SESSION_COOKIE_SECURE=0 关闭
_secure = os.environ.get("SESSION_COOKIE_SECURE", "").lower()
if _secure in ("1", "true", "yes") or (_is_production() and _secure not in ("0", "false", "no")):
    app.config["SESSION_COOKIE_SECURE"] = True
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB uploads


PW_FILE = ROOT / "data" / ".access_password_hash"


def _custom_hash() -> str:
    try:
        return PW_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _check_password(password: str) -> bool:
    """优先使用页面里改过的密码（哈希存盘）；否则用 APP_PASSWORD。"""
    from werkzeug.security import check_password_hash

    h = _custom_hash()
    if h:
        return bool(password) and check_password_hash(h, password)
    expected = _load_password()
    return bool(expected) and secrets.compare_digest(password, expected)


def _load_password() -> str:
    """密码只来自 APP_PASSWORD；本地开发可回退 .app_password。生产环境禁止默认/空密码。"""
    env = os.environ.get("APP_PASSWORD", "").strip()
    if env:
        return env
    if _is_production():
        return ""
    p = ROOT / ".app_password"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return ""


# 生产启动时强制要求 APP_PASSWORD（无默认密码）
if _is_production() and not os.environ.get("APP_PASSWORD", "").strip():
    raise SystemExit("生产环境必须设置环境变量 APP_PASSWORD，拒绝使用默认密码启动")


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("authed"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "unauthorized"}), 401
            return redirect(url_for("login_page", next=request.path))
        return fn(*args, **kwargs)

    return wrapper


# ---------- pages ----------
@app.get("/login")
def login_page():
    if session.get("authed"):
        return redirect("/")
    return send_from_directory(TEMPLATES, "login.html")


@app.post("/api/login")
def api_login():
    data = request.get_json(silent=True) or {}
    password = (data.get("password") or request.form.get("password") or "").strip()
    if not _custom_hash() and not _load_password():
        return jsonify({"ok": False, "error": "服务端未配置密码"}), 500
    if not _check_password(password):
        return jsonify({"ok": False, "error": "密码错误"}), 401
    session["authed"] = True
    session.permanent = True
    return jsonify({"ok": True})


@app.get("/password")
@login_required
def password_page():
    return send_from_directory(TEMPLATES, "password.html")


@app.post("/api/password")
@login_required
def api_password():
    from werkzeug.security import generate_password_hash

    data = request.get_json(silent=True) or request.form
    new = (data.get("new_password") or "").strip()
    confirm = (data.get("confirm_password") or "").strip()
    if len(new) < 6:
        return jsonify({"ok": False, "error": "新密码至少 6 位"}), 400
    if new != confirm:
        return jsonify({"ok": False, "error": "两次输入不一致"}), 400
    PW_FILE.parent.mkdir(parents=True, exist_ok=True)
    PW_FILE.write_text(generate_password_hash(new), encoding="utf-8")
    try:
        os.chmod(PW_FILE, 0o600)
    except OSError:
        pass
    return jsonify({"ok": True})


@app.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/me")
def api_me():
    return jsonify({"ok": True, "authed": bool(session.get("authed")), "llm": llm_configured()})


@app.get("/")
@login_required
def index():
    return send_from_directory(TEMPLATES, "index.html")


@app.get("/manifest.json")
def manifest():
    return send_from_directory(STATIC, "manifest.json")


@app.get("/sw.js")
def service_worker():
    # SW must be at root scope
    resp = send_from_directory(STATIC, "sw.js")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


# ---------- API ----------
@app.get("/api/styles")
@login_required
def api_styles():
    return jsonify({"ok": True, "styles": STYLES, "default_avatar": DEFAULT_AVATAR, "assumptions": DEFAULT_ASSUMPTIONS})


@app.get("/api/stores")
@login_required
def api_stores():
    return jsonify({"ok": True, "stores": list_stores()})


@app.get("/api/stores/<name>")
@login_required
def api_store_get(name: str):
    data = load_store(name)
    if not data:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "store": data})


@app.post("/api/stores")
@login_required
def api_store_save():
    store = request.get_json(silent=True) or {}
    if not store.get("name"):
        return jsonify({"ok": False, "error": "店名必填"}), 400
    store["avatar"] = ensure_avatar(store.get("avatar"))
    store.setdefault("_meta", {})
    store["_meta"]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai")
    path = save_store(store)
    return jsonify({"ok": True, "path": str(path), "store": store})


@app.post("/api/stores/<name>/photos")
@login_required
def api_store_photos(name: str):
    if "files" not in request.files and "file" not in request.files:
        # accept multiple under 'files' or single 'file'
        files = request.files.getlist("photos") or []
    else:
        files = request.files.getlist("files") or request.files.getlist("file") or request.files.getlist("photos")
    if not files:
        return jsonify({"ok": False, "error": "无文件"}), 400
    pdir = photos_dir(name)
    saved = []
    for f in files:
        if not f or not f.filename:
            continue
        # sanitize filename
        fname = Path(f.filename).name
        dest = pdir / fname
        f.save(dest)
        saved.append(str(dest))
    return jsonify({"ok": True, "saved": saved})


@app.post("/api/generate")
@login_required
def api_generate():
    body = request.get_json(silent=True) or {}
    store = body.get("store") or {}
    n = int(body.get("n") or 3)
    n = max(1, min(5, n))
    use_llm = bool(body.get("use_llm"))
    style_ids = body.get("style_ids") or store.get("preferred_styles") or None

    missing = [k for k in ["name", "city", "category", "avg_price"] if not (store.get(k) or "").strip()]
    if missing or not store.get("dishes") or not store.get("sell_points"):
        return jsonify({"ok": False, "error": "请完整填写店名、城市、品类、主打菜、人均、卖点", "missing": missing}), 400

    store["avatar"] = ensure_avatar(store.get("avatar"))

    if use_llm and llm_configured():
        versions = generate_with_llm(store, n=n, style_ids=style_ids)
    else:
        versions = generate_versions(store, n=n, style_ids=style_ids)

    results = []
    for v in versions:
        segs = segment_script(v["full_script"])
        segs_with = build_prompts_for_version(segs, store, avatar=store.get("avatar"))
        results.append({**v, "segments": segs_with})

    return jsonify({"ok": True, "versions": results, "llm": use_llm and llm_configured()})


@app.post("/api/segment")
@login_required
def api_segment():
    body = request.get_json(silent=True) or {}
    text = body.get("text") or ""
    segs = segment_script(text)
    return jsonify({"ok": True, "segments": segs})


@app.post("/api/prompts")
@login_required
def api_prompts():
    body = request.get_json(silent=True) or {}
    store = body.get("store") or {}
    segments = body.get("segments") or []
    out = build_prompts_for_version(segments, store, avatar=store.get("avatar"))
    return jsonify({"ok": True, "segments": out})


@app.post("/api/ad-estimate")
@login_required
def api_ad_estimate():
    body = request.get_json(silent=True) or {}
    budget = float(body.get("budget") or 100)
    assumptions = body.get("assumptions") or {}
    goal = body.get("goal") or "拉新到店"
    est = estimate_douyin(budget=budget, assumptions=assumptions, goal=goal)
    return jsonify({"ok": True, "estimate": est})


@app.post("/api/export/markdown")
@login_required
def api_export_md():
    body = request.get_json(silent=True) or {}
    store = body.get("store") or {}
    versions = body.get("versions") or []
    est = body.get("ad_estimate") or {}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai")
    lines = [
        f"# {store.get('name', '店铺')} · 口播方案",
        "",
        f"> 导出时间：{now}",
        "",
        "## 店铺",
        f"- 城市：{store.get('city')}",
        f"- 品类：{store.get('category')}",
        f"- 主打菜：{'、'.join(store.get('dishes') or [])}",
        f"- 人均：{store.get('avg_price')}",
        f"- 卖点：{'；'.join(store.get('sell_points') or [])}",
        f"- 目标：{store.get('goal')}",
        "",
    ]
    for i, v in enumerate(versions):
        lines += [
            f"## 版本 {i+1} · {v.get('style_name')}",
            f"**钩子：** {v.get('hook')}",
            "",
            f"**正文：** {v.get('body')}",
            "",
            f"**CTA：** {v.get('cta')}",
            "",
            "### 分段",
        ]
        for seg in v.get("segments") or []:
            lines.append(f"{seg.get('index')}. （{seg.get('chars')}字/{seg.get('seconds')}s）{seg.get('text')}")
            vp = seg.get("video_prompt") or {}
            if vp.get("prompt_en"):
                lines.append("")
                lines.append("```")
                lines.append(vp["prompt_en"])
                lines.append("```")
            lines.append("")
    if est:
        lines += [
            f"## 投流参考（预算 {est.get('budget')} 元）",
            "",
            f"**{est.get('disclaimer', '仅供参考，不构成收益保证')}**",
            "",
            f"- 曝光：{est.get('impressions')}",
            f"- 点击：{est.get('clicks')}",
            f"- 到店/核销：{est.get('to_store_or_redeem')}",
            "",
        ]
    return jsonify({"ok": True, "markdown": "\n".join(lines), "filename": f"{store.get('name','koubo')}_koubo.md"})


@app.get("/api/example")
@login_required
def api_example():
    store = {
        "name": "老王烧烤",
        "city": "成都·建设路",
        "category": "烧烤",
        "dishes": ["羊肉串", "烤茄子", "蒜蓉生蚝"],
        "avg_price": "75元",
        "sell_points": ["炭火现烤不蘸料也香", "夜宵常备座位", "本地回头客多"],
        "goal": "拉新到店",
        "group_price": "59.9元双人餐",
        "reference_script": "",
        "preferred_styles": ["tancha_fancha", "jiage_chongji", "xuanian_gookou"],
        "avatar": dict(DEFAULT_AVATAR),
        "_meta": {"note": "【示例数据】仅供演示，非真实门店", "is_example": True},
    }
    return jsonify({"ok": True, "store": store})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8600"))
    app.run(host="0.0.0.0", port=port, debug=False)
