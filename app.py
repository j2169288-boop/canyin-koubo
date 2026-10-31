"""餐饮数字人口播工具 — Streamlit MVP"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lib.ad_estimate import DEFAULT_ASSUMPTIONS, estimate_douyin
from lib.llm import generate_with_llm, llm_configured
from lib.segmenter import segment_script
from lib.store_config import (
    default_store_template,
    list_stores,
    load_store,
    photos_dir,
    save_store,
)
from lib.templates import STYLES, generate_versions
from lib.video_prompts import DEFAULT_AVATAR, build_prompts_for_version, ensure_avatar


st.set_page_config(
    page_title="餐饮数字人口播工具",
    page_icon="🍜",
    layout="wide",
)

st.title("🍜 餐饮数字人口播工具")
st.caption("给餐饮老板用的简易口播文案 / 分段 / 数字人视频提示词 / 投流参考 · MVP")

# ---------- 侧边栏：店铺加载 & API 状态 ----------
with st.sidebar:
    st.header("店铺配置")
    stores = list_stores()
    pick = st.selectbox("加载已有店铺", ["（新建）"] + stores)
    if st.button("加载", disabled=(pick == "（新建）")):
        data = load_store(pick)
        if data:
            st.session_state["store"] = data
            st.success(f"已加载：{pick}")
        else:
            st.error("加载失败")

    st.divider()
    st.subheader("LLM 状态")
    if llm_configured():
        st.success("已检测到 API Key（将优先走 LLM）")
        st.caption("环境变量：OPENAI_API_KEY 或 XAI_API_KEY；可选 OPENAI_BASE_URL / OPENAI_MODEL")
    else:
        st.info("未配置 API Key → 使用内置模板引擎")
        st.caption("可选：export OPENAI_API_KEY=... OPENAI_BASE_URL=https://api.x.ai/v1")

    st.divider()
    st.markdown("**数据目录**")
    st.code(str(ROOT / "data" / "stores"), language=None)


def _init_store():
    if "store" not in st.session_state:
        st.session_state["store"] = default_store_template()


_init_store()
store = st.session_state["store"]

# ---------- 表单 ----------
st.header("① 店铺信息")
c1, c2, c3 = st.columns(3)
with c1:
    name = st.text_input("店名 *", value=store.get("name") or "")
    city = st.text_input("城市/商圈 *", value=store.get("city") or "", placeholder="例：上海·静安寺")
    category = st.text_input("品类 *", value=store.get("category") or "", placeholder="例：烧烤/火锅/面馆")
with c2:
    dishes_raw = st.text_area(
        "主打菜（每行一个）*",
        value="\n".join(store.get("dishes") or []),
        height=100,
    )
    avg_price = st.text_input("人均 *", value=store.get("avg_price") or "", placeholder="例：68元")
    group_price = st.text_input("团购价（可选）", value=store.get("group_price") or "", placeholder="例：39.9元双人餐")
with c3:
    sells_raw = st.text_area(
        "卖点（每行一条）*",
        value="\n".join(store.get("sell_points") or []),
        height=100,
    )
    goal = st.selectbox(
        "目标",
        ["拉新到店", "推团购", "品牌人设"],
        index=["拉新到店", "推团购", "品牌人设"].index(store.get("goal") or "拉新到店"),
    )
    style_names = [s["name"] for s in STYLES]
    preferred = store.get("preferred_styles") or []
    default_ix = [i for i, s in enumerate(STYLES) if s["id"] in preferred] or list(range(min(3, len(STYLES))))
    picked_styles = st.multiselect(
        "生成风格（可多选）",
        style_names,
        default=[style_names[i] for i in default_ix],
    )
    n_versions = st.slider("生成版本数", 1, 5, min(3, max(1, len(picked_styles) or 3)))

ref_script = st.text_area(
    "对标视频文案（可选，粘贴文本作风格参考；勿依赖外链抓取）",
    value=store.get("reference_script") or "",
    height=80,
    placeholder="把对标口播的文案粘贴到这里……",
)

use_llm = st.checkbox("尝试使用 LLM（需配置 API Key，失败自动回退模板）", value=llm_configured())

# 数字人形象
with st.expander("数字人形象（多段视频保持一致，保存在店铺配置）", expanded=False):
    av = ensure_avatar(store.get("avatar"))
    a1, a2 = st.columns(2)
    with a1:
        av["appearance_zh"] = st.text_input("人物外观（中文）", value=av["appearance_zh"])
        av["outfit_zh"] = st.text_input("服装（中文）", value=av["outfit_zh"])
        av["scene_zh"] = st.text_input("场景（中文）", value=av["scene_zh"])
        av["camera_zh"] = st.text_input("机位（中文）", value=av["camera_zh"])
    with a2:
        av["appearance_en"] = st.text_input("Appearance (EN)", value=av["appearance_en"])
        av["outfit_en"] = st.text_input("Outfit (EN)", value=av["outfit_en"])
        av["scene_en"] = st.text_input("Scene (EN)", value=av["scene_en"])
        av["camera_en"] = st.text_input("Camera (EN)", value=av["camera_en"])

# 照片上传
uploaded = st.file_uploader("上传门头/招牌菜/店内照片", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)

# ---------- 组装 store ----------
def collect_store() -> dict:
    dishes = [x.strip() for x in dishes_raw.splitlines() if x.strip()]
    sells = [x.strip() for x in sells_raw.splitlines() if x.strip()]
    style_ids = [s["id"] for s in STYLES if s["name"] in picked_styles]
    return {
        "name": name.strip(),
        "city": city.strip(),
        "category": category.strip(),
        "dishes": dishes,
        "avg_price": avg_price.strip(),
        "sell_points": sells,
        "goal": goal,
        "group_price": group_price.strip(),
        "reference_script": ref_script.strip(),
        "preferred_styles": style_ids,
        "avatar": ensure_avatar(av),
        "_meta": {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
            "note": "店铺配置；示例数据请自行替换为真实信息",
        },
    }


b1, b2, b3 = st.columns(3)
with b1:
    save_clicked = st.button("💾 保存店铺配置", use_container_width=True)
with b2:
    gen_clicked = st.button("✨ 生成口播方案", type="primary", use_container_width=True)
with b3:
    example_clicked = st.button("填入示例「老王烧烤」", use_container_width=True)

if example_clicked:
    st.session_state["store"] = {
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
        "_meta": {
            "note": "【示例数据】仅供演示，非真实门店",
            "is_example": True,
        },
    }
    st.rerun()

if save_clicked:
    s = collect_store()
    if not s["name"]:
        st.error("请先填写店名")
    else:
        path = save_store(s)
        # 保存照片
        if uploaded:
            pdir = photos_dir(s["name"])
            for f in uploaded:
                dest = pdir / f.name
                dest.write_bytes(f.getbuffer())
        st.session_state["store"] = s
        st.success(f"已保存：{path}")

# ---------- 生成 ----------
if gen_clicked:
    s = collect_store()
    missing = [k for k in ["name", "city", "category", "avg_price"] if not s.get(k)]
    if missing or not s["dishes"] or not s["sell_points"]:
        st.error("请完整填写店名、城市、品类、主打菜、人均、卖点")
    else:
        st.session_state["store"] = s
        style_ids = s["preferred_styles"] or None
        if use_llm and llm_configured():
            versions = generate_with_llm(s, n=n_versions, style_ids=style_ids)
        else:
            versions = generate_versions(s, n=n_versions, style_ids=style_ids)

        results = []
        for v in versions:
            segs = segment_script(v["full_script"])
            segs_with_prompts = build_prompts_for_version(segs, s, avatar=s.get("avatar"))
            results.append({**v, "segments": segs_with_prompts})
        st.session_state["results"] = results
        st.session_state["result_store"] = s

# ---------- 结果展示 ----------
results = st.session_state.get("results")
result_store = st.session_state.get("result_store")

if results and result_store:
    st.header("② 口播文案 & 分段 & 视频提示词")
    if result_store.get("_meta", {}).get("is_example"):
        st.warning("当前为【示例数据·老王烧烤】，仅供演示，非真实门店。")

    for i, v in enumerate(results):
        with st.expander(
            f"版本 {i+1} · {v.get('style_name')}（{v.get('source', 'template')}）",
            expanded=(i == 0),
        ):
            if v.get("llm_error"):
                st.caption(f"LLM 失败已回退模板：{v['llm_error']}")
            st.markdown("**前3秒钩子**")
            st.write(v["hook"])
            st.markdown("**正文**")
            st.write(v["body"])
            st.markdown("**行动号召**")
            st.write(v["cta"])
            st.markdown("**完整文案**")
            st.text_area("full", v["full_script"], height=100, key=f"full_{i}", label_visibility="collapsed")

            st.markdown("**短视频分段（≤15秒，约 4.2 字/秒）**")
            for seg in v["segments"]:
                st.markdown(
                    f"- 片段 {seg['index']} · {seg['chars']}字 · 约 **{seg['seconds']}秒**  \n"
                    f"  {seg['text']}"
                )
                with st.popover(f"视频 Prompt · 片段{seg['index']}"):
                    vp = seg["video_prompt"]
                    st.markdown(vp["explain_zh"])
                    st.code(vp["prompt_en"], language=None)

    # ---------- 投流 ----------
    st.header("③ 抖音投流预估参考")
    st.error("⚠️ 仅供参考，不构成收益保证。实际效果因素材、竞争、位置差异极大。")
    st.caption("参数来源：内置「行业经验参考假设」，可在下方自行调整。")

    budget = st.number_input("预算（元）", min_value=10.0, max_value=100000.0, value=100.0, step=10.0)
    with st.expander("调整假设参数（CPM / CTR / 到店转化）"):
        col = st.columns(3)
        assumptions = {}
        with col[0]:
            assumptions["cpm_low"] = st.number_input("CPM 低(元/千次)", value=DEFAULT_ASSUMPTIONS["cpm_low"])
            assumptions["cpm_mid"] = st.number_input("CPM 中", value=DEFAULT_ASSUMPTIONS["cpm_mid"])
            assumptions["cpm_high"] = st.number_input("CPM 高", value=DEFAULT_ASSUMPTIONS["cpm_high"])
        with col[1]:
            assumptions["ctr_low"] = st.number_input("CTR 低", value=DEFAULT_ASSUMPTIONS["ctr_low"], format="%.4f")
            assumptions["ctr_mid"] = st.number_input("CTR 中", value=DEFAULT_ASSUMPTIONS["ctr_mid"], format="%.4f")
            assumptions["ctr_high"] = st.number_input("CTR 高", value=DEFAULT_ASSUMPTIONS["ctr_high"], format="%.4f")
        with col[2]:
            assumptions["to_store_low"] = st.number_input("到店转化 低", value=DEFAULT_ASSUMPTIONS["to_store_low"], format="%.3f")
            assumptions["to_store_mid"] = st.number_input("到店转化 中", value=DEFAULT_ASSUMPTIONS["to_store_mid"], format="%.3f")
            assumptions["to_store_high"] = st.number_input("到店转化 高", value=DEFAULT_ASSUMPTIONS["to_store_high"], format="%.3f")

    est = estimate_douyin(budget=budget, assumptions=assumptions, goal=result_store.get("goal") or "拉新到店")
    st.session_state["ad_estimate"] = est

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("曝光（低/中/高）", f"{est['impressions']['low']} / {est['impressions']['mid']} / {est['impressions']['high']}")
    with m2:
        st.metric("点击（低/中/高）", f"{est['clicks']['low']} / {est['clicks']['mid']} / {est['clicks']['high']}")
    with m3:
        st.metric("到店/核销（低/中/高）", f"{est['to_store_or_redeem']['low']} / {est['to_store_or_redeem']['mid']} / {est['to_store_or_redeem']['high']}")

    st.markdown("**定向建议**")
    for k, v in est["targeting"].items():
        st.write(f"- {k}：{v}")
    st.markdown("**投放时段建议**")
    for t in est["time_slots"]:
        st.write(f"- {t}")
    for n in est["notes"]:
        st.caption(n)

    # ---------- 导出 ----------
    st.header("④ 导出")
    export_obj = {
        "store": result_store,
        "versions": results,
        "ad_estimate": est,
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S Asia/Shanghai"),
    }
    md_lines = [
        f"# {result_store['name']} · 口播方案",
        f"",
        f"> 导出时间：{export_obj['exported_at']}",
        f"",
        f"## 店铺",
        f"- 城市：{result_store.get('city')}",
        f"- 品类：{result_store.get('category')}",
        f"- 主打菜：{'、'.join(result_store.get('dishes') or [])}",
        f"- 人均：{result_store.get('avg_price')}",
        f"- 卖点：{'；'.join(result_store.get('sell_points') or [])}",
        f"- 目标：{result_store.get('goal')}",
        f"",
    ]
    for i, v in enumerate(results):
        md_lines += [
            f"## 版本 {i+1} · {v.get('style_name')}",
            f"**钩子：** {v['hook']}",
            f"",
            f"**正文：** {v['body']}",
            f"",
            f"**CTA：** {v['cta']}",
            f"",
            f"### 分段",
        ]
        for seg in v["segments"]:
            md_lines.append(f"{seg['index']}. （{seg['chars']}字/{seg['seconds']}s）{seg['text']}")
            md_lines.append(f"")
            md_lines.append(f"```")
            md_lines.append(seg["video_prompt"]["prompt_en"])
            md_lines.append(f"```")
            md_lines.append(f"")
    md_lines += [
        f"## 投流参考（预算 {est['budget']} 元）",
        f"",
        f"**{est['disclaimer']}**",
        f"",
        f"- 曝光 低/中/高：{est['impressions']}",
        f"- 点击 低/中/高：{est['clicks']}",
        f"- 到店/核销 低/中/高：{est['to_store_or_redeem']}",
        f"",
    ]
    md_text = "\n".join(md_lines)
    json_text = json.dumps(export_obj, ensure_ascii=False, indent=2)

    e1, e2 = st.columns(2)
    with e1:
        st.download_button("⬇️ 导出 Markdown", md_text, file_name=f"{result_store['name']}_koubo.md", mime="text/markdown")
    with e2:
        st.download_button("⬇️ 导出 JSON", json_text, file_name=f"{result_store['name']}_koubo.json", mime="application/json")

st.divider()
st.caption("本地 MVP · 模板引擎默认可用 · LLM 为可选增强 · 投流数字均为行业经验参考假设")
