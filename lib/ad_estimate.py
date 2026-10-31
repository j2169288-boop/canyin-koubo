"""抖音 DOU+/本地推 投流预估（行业经验参考，非收益保证）。"""
from __future__ import annotations

from typing import Dict, Any


# 默认假设参数（可在界面调整），均标注为「行业经验参考假设」
DEFAULT_ASSUMPTIONS = {
    "cpm_low": 20.0,       # 元/千次曝光
    "cpm_mid": 40.0,
    "cpm_high": 80.0,
    "ctr_low": 0.008,      # 点击率 0.8%
    "ctr_mid": 0.015,      # 1.5%
    "ctr_high": 0.030,     # 3%
    "to_store_low": 0.02,  # 点击到店/核销转化 2%
    "to_store_mid": 0.05,  # 5%
    "to_store_high": 0.10, # 10%
}


TARGETING_TIPS = {
    "拉新到店": {
        "距离": "店铺周边 3–5 公里优先；餐饮可试 1–3 公里高密度",
        "年龄": "25–45（家庭聚餐可放宽到 22–50）",
        "兴趣": "美食、本地生活、探店、夜宵/烧烤等品类相关",
    },
    "推团购": {
        "距离": "店铺周边 5–8 公里，覆盖通勤与周末出行",
        "年龄": "22–40，对价格敏感人群",
        "兴趣": "团购优惠、本地生活、美食探店",
    },
    "品牌人设": {
        "距离": "本市或商圈周边 8–15 公里，偏品牌认知",
        "年龄": "按品类：年轻潮流 18–30；家常/宴请 28–50",
        "兴趣": "美食、生活方式、本地好物",
    },
}

TIME_SLOTS = [
    "午市前 10:30–11:30（决策窗口，适合堂食拉新）",
    "晚市前 16:30–17:30（下班决策，适合到店/团购）",
    "夜宵时段 21:00–23:00（烧烤/夜宵品类优先）",
    "周末 11:00–13:00 / 17:00–19:00（家庭聚餐高峰）",
]


def estimate_douyin(
    budget: float = 100.0,
    assumptions: Dict[str, float] | None = None,
    goal: str = "拉新到店",
) -> Dict[str, Any]:
    """
    根据预算和假设参数，计算曝光/点击/到店 的低-中-高区间。
    公式：曝光 = 预算 / CPM * 1000；点击 = 曝光 * CTR；到店 = 点击 * 转化率
    注意：低曝光对应高 CPM，高转化对应乐观假设，区间交叉组合给出保守/中位/乐观。
    """
    a = {**DEFAULT_ASSUMPTIONS, **(assumptions or {})}
    budget = max(float(budget), 1.0)

    # 曝光：预算/CPM*1000 —— CPM 越高曝光越少
    impressions = {
        "low": int(budget / a["cpm_high"] * 1000),
        "mid": int(budget / a["cpm_mid"] * 1000),
        "high": int(budget / a["cpm_low"] * 1000),
    }
    clicks = {
        "low": int(impressions["low"] * a["ctr_low"]),
        "mid": int(impressions["mid"] * a["ctr_mid"]),
        "high": int(impressions["high"] * a["ctr_high"]),
    }
    to_store = {
        "low": max(1, int(clicks["low"] * a["to_store_low"])) if clicks["low"] else 0,
        "mid": max(1, int(clicks["mid"] * a["to_store_mid"])) if clicks["mid"] else 0,
        "high": int(clicks["high"] * a["to_store_high"]),
    }

    targeting = TARGETING_TIPS.get(goal, TARGETING_TIPS["拉新到店"])

    return {
        "budget": budget,
        "disclaimer": "仅供参考，不构成收益保证。实际效果受素材、时段、竞争、门店位置等影响极大。",
        "assumptions": a,
        "impressions": impressions,
        "clicks": clicks,
        "to_store_or_redeem": to_store,
        "targeting": targeting,
        "time_slots": TIME_SLOTS,
        "notes": [
            "CPM/CTR/转化率为行业经验参考假设，可在界面自行调整。",
            "「到店/核销」为点击后的粗估转化，非平台回传精准值。",
            "建议先小额测素材，再加预算；同预算下素材质量往往比定向更重要。",
        ],
    }
