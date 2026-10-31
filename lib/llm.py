"""可选 LLM 文案生成（OpenAI 兼容接口，如 xAI https://api.x.ai/v1）。无 key 时回退模板。"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .templates import STYLES, generate_versions


def llm_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("XAI_API_KEY"))


def _api_settings() -> Dict[str, str]:
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("XAI_API_KEY") or ""
    base = os.environ.get("OPENAI_BASE_URL") or os.environ.get("XAI_BASE_URL") or "https://api.x.ai/v1"
    model = os.environ.get("OPENAI_MODEL") or os.environ.get("XAI_MODEL") or "grok-2-latest"
    base = base.rstrip("/")
    return {"key": key, "base": base, "model": model}


def _chat(messages: List[Dict[str, str]], temperature: float = 0.8) -> str:
    cfg = _api_settings()
    url = f"{cfg['base']}/chat/completions"
    body = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['key']}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def generate_with_llm(
    store: Dict[str, Any],
    n: int = 3,
    style_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    调用 LLM 生成多版口播；失败或未配置时回退模板。
    若有 reference_script，要求模型先拆解风格再仿写（不照抄事实数据）。
    """
    if not llm_configured():
        return generate_versions(store, n=n, style_ids=style_ids)

    style_map = {s["id"]: s for s in STYLES}
    order = style_ids or [s["id"] for s in STYLES]
    order = order[:n]
    style_desc = "\n".join(
        f"- {sid}: {style_map[sid]['name']} — {style_map[sid]['desc']}"
        for sid in order
        if sid in style_map
    )

    ref = (store.get("reference_script") or "").strip()
    ref_block = ""
    if ref:
        ref_block = (
            "\n对标口播文案（仅作节奏/语气/结构参考，禁止照搬其店名、价格、菜品等事实；"
            "本店事实以用户输入为准）：\n---\n"
            f"{ref[:2000]}\n---\n"
        )

    system = (
        "你是短视频餐饮口播文案写手。只使用用户提供的店铺事实，不要编造地址、电话、销量、排行榜等。"
        "每版输出 JSON 对象，字段：style_id, style_name, hook, body, cta, full_script。"
        "hook 控制在前3秒能说完（约12–20字），口语化，适合竖屏口播。"
        "最终只输出一个 JSON 数组，不要 markdown 围栏。"
    )
    user = (
        f"店铺事实：\n"
        f"- 店名：{store.get('name')}\n"
        f"- 城市/商圈：{store.get('city')}\n"
        f"- 品类：{store.get('category')}\n"
        f"- 主打菜：{', '.join(store.get('dishes') or [])}\n"
        f"- 人均：{store.get('avg_price')}\n"
        f"- 卖点：{', '.join(store.get('sell_points') or [])}\n"
        f"- 目标：{store.get('goal')}\n"
        f"- 团购价：{store.get('group_price') or '无'}\n"
        f"{ref_block}\n"
        f"请按以下风格各写 1 版，共 {len(order)} 版：\n{style_desc}\n"
    )

    try:
        raw = _chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:].strip()
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("LLM 未返回数组")
        out = []
        for item in data[:n]:
            hook = item.get("hook") or ""
            body = item.get("body") or ""
            cta = item.get("cta") or ""
            full = item.get("full_script") or f"{hook}{body}{cta}"
            out.append(
                {
                    "style_id": item.get("style_id") or "llm",
                    "style_name": item.get("style_name") or "LLM",
                    "hook": hook,
                    "body": body,
                    "cta": cta,
                    "full_script": full,
                    "source": "llm",
                }
            )
        if out:
            return out
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as e:
        # 回退模板，并在首版标注
        fallback = generate_versions(store, n=n, style_ids=style_ids)
        if fallback:
            fallback[0]["llm_error"] = str(e)
            fallback[0]["source"] = "template_fallback"
        return fallback

    return generate_versions(store, n=n, style_ids=style_ids)
