#!/usr/bin/env python3
"""核心逻辑冒烟测试：生成 / 分段 / prompt / 投流。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.ad_estimate import estimate_douyin
from lib.segmenter import segment_script, estimate_seconds
from lib.store_config import save_store, load_store
from lib.templates import generate_versions, STYLES
from lib.video_prompts import build_prompts_for_version


def main() -> int:
    store = {
        "name": "老王烧烤",
        "city": "成都·建设路",
        "category": "烧烤",
        "dishes": ["羊肉串", "烤茄子", "蒜蓉生蚝"],
        "avg_price": "75元",
        "sell_points": ["炭火现烤不蘸料也香", "夜宵常备座位", "本地回头客多"],
        "goal": "拉新到店",
        "group_price": "59.9元双人餐",
        "_meta": {"note": "【示例数据】仅供演示，非真实门店", "is_example": True},
    }

    print("=== 1. 模板生成（5 风格）===")
    versions = generate_versions(store, n=5)
    assert len(versions) == 5, versions
    assert len(STYLES) >= 5
    for v in versions:
        assert v["hook"] and v["body"] and v["cta"] and v["full_script"]
        print(f"  [{v['style_name']}] hook={v['hook'][:24]}…  full_len={len(v['full_script'])}")

    print("\n=== 2. 分段 ≤15s ===")
    segs = segment_script(versions[0]["full_script"])
    assert segs, "分段为空"
    for s in segs:
        assert s["seconds"] <= 15.5, s  # 允许四舍五入误差
        print(f"  #{s['index']} {s['chars']}字/{s['seconds']}s | {s['text'][:40]}…")
    assert estimate_seconds("一二三四") == round(4 / 4.2, 1)

    print("\n=== 3. 视频 Prompt ===")
    with_p = build_prompts_for_version(segs, store)
    assert with_p[0]["video_prompt"]["prompt_en"]
    assert "9:16" in with_p[0]["video_prompt"]["prompt_en"]
    assert "Lip-sync" in with_p[0]["video_prompt"]["prompt_en"]
    print(with_p[0]["video_prompt"]["prompt_en"][:200], "…")
    print(with_p[0]["video_prompt"]["explain_zh"][:120], "…")

    print("\n=== 4. 投流估算（100元）===")
    est = estimate_douyin(100)
    assert est["impressions"]["low"] < est["impressions"]["high"]
    assert "仅供参考" in est["disclaimer"]
    print(f"  曝光: {est['impressions']}")
    print(f"  点击: {est['clicks']}")
    print(f"  到店: {est['to_store_or_redeem']}")

    print("\n=== 5. 店铺 JSON 存取 ===")
    path = save_store(store)
    loaded = load_store("老王烧烤")
    assert loaded and loaded["name"] == "老王烧烤"
    print(f"  saved → {path}")

    # 打印一份节选供汇报
    excerpt = {
        "version_1": {
            "style": versions[0]["style_name"],
            "hook": versions[0]["hook"],
            "body": versions[0]["body"],
            "cta": versions[0]["cta"],
            "segments": [
                {"index": s["index"], "chars": s["chars"], "seconds": s["seconds"], "text": s["text"]}
                for s in segs
            ],
            "video_prompt_sample": with_p[0]["video_prompt"]["prompt_en"],
        },
        "ad_estimate_100yuan": {
            "impressions": est["impressions"],
            "clicks": est["clicks"],
            "to_store_or_redeem": est["to_store_or_redeem"],
            "disclaimer": est["disclaimer"],
        },
    }
    out = ROOT / "data" / "stores" / "老王烧烤" / "test_excerpt.json"
    out.write_text(json.dumps(excerpt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n节选已写: {out}")
    print("\nALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
