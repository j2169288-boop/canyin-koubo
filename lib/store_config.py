"""店铺配置 JSON 保存 / 加载。"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .video_prompts import DEFAULT_AVATAR, ensure_avatar


ROOT = Path(__file__).resolve().parent.parent


def data_root() -> Path:
    """数据根目录：可用环境变量 DATA_DIR 覆盖（Render 等临时盘场景）。"""
    env = (os.environ.get("DATA_DIR") or "").strip()
    if env:
        return Path(env)
    return ROOT / "data"


def stores_dir() -> Path:
    d = data_root() / "stores"
    d.mkdir(parents=True, exist_ok=True)
    return d


# 兼容旧引用名（导入时解析一次；运行中请用 stores_dir()）
STORES_DIR = stores_dir()


def _safe_name(name: str) -> str:
    name = (name or "未命名店铺").strip()
    name = re.sub(r"[\\/:*?\"<>|\s]+", "_", name)
    return name[:64] or "store"


def store_dir(name: str) -> Path:
    d = stores_dir() / _safe_name(name)
    d.mkdir(parents=True, exist_ok=True)
    (d / "photos").mkdir(exist_ok=True)
    return d


def config_path(name: str) -> Path:
    return store_dir(name) / "config.json"


def list_stores() -> List[str]:
    names = []
    for p in sorted(stores_dir().glob("*/config.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            names.append(data.get("name") or p.parent.name)
        except Exception:
            names.append(p.parent.name)
    return names


def save_store(store: Dict[str, Any]) -> Path:
    name = store.get("name") or "未命名店铺"
    store = dict(store)
    store["avatar"] = ensure_avatar(store.get("avatar"))
    path = config_path(name)
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_store(name: str) -> Optional[Dict[str, Any]]:
    path = config_path(name)
    if not path.exists():
        for p in stores_dir().glob("*/config.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if data.get("name") == name or p.parent.name == _safe_name(name):
                    data["avatar"] = ensure_avatar(data.get("avatar"))
                    return data
            except Exception:
                continue
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    data["avatar"] = ensure_avatar(data.get("avatar"))
    return data


def photos_dir(name: str) -> Path:
    return store_dir(name) / "photos"


def default_store_template() -> Dict[str, Any]:
    return {
        "name": "",
        "city": "",
        "category": "",
        "dishes": [],
        "avg_price": "",
        "sell_points": [],
        "goal": "拉新到店",
        "group_price": "",
        "reference_script": "",
        "preferred_styles": [],
        "avatar": dict(DEFAULT_AVATAR),
        "_meta": {"note": "店铺配置，可复用数字人形象与风格偏好"},
    }
