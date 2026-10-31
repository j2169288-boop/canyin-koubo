"""口播文案模板 + 规则引擎（无 LLM 时的默认路径）。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


STYLES = [
    {
        "id": "tancha_fancha",
        "name": "探店反差",
        "desc": "先抛出「看起来不起眼/贵/小」再反转美味或性价比",
    },
    {
        "id": "laoban_zishu",
        "name": "老板自述",
        "desc": "第一人称讲坚持与用心，建立信任",
    },
    {
        "id": "jiage_chongji",
        "name": "价格冲击",
        "desc": "用人均/团购价制造「划算感」冲击",
    },
    {
        "id": "tongdian_zhongcao",
        "name": "痛点种草",
        "desc": "先戳痛点（排队/踩雷/没地方吃）再给解法",
    },
    {
        "id": "xuanian_gookou",
        "name": "悬念钩子",
        "desc": "前3秒留悬念，中间揭秘，结尾强行动号召",
    },
]


def _join_dishes(dishes: List[str], limit: int = 3) -> str:
    dishes = [d.strip() for d in dishes if d and str(d).strip()]
    if not dishes:
        return "招牌菜"
    return "、".join(dishes[:limit])


def _join_sells(sells: List[str], limit: int = 2) -> str:
    sells = [s.strip() for s in sells if s and str(s).strip()]
    if not sells:
        return "味道扎实、回头客多"
    return "，".join(sells[:limit])


def _cta(goal: str, store_name: str, group_price: Optional[str] = None) -> str:
    if goal == "推团购":
        if group_price:
            return f"想吃的扣1，团购只要{group_price}，导航搜「{store_name}」直接核销。"
        return f"想吃的扣1，主页团购下单，导航搜「{store_name}」到店核销。"
    if goal == "品牌人设":
        return f"记住这家「{store_name}」，下次路过别错过，关注我不迷路。"
    # 默认拉新到店
    return f"就在附近的朋友，导航搜「{store_name}」，今天就来尝尝！"


def generate_versions(
    store: Dict[str, Any],
    n: int = 3,
    style_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    基于模板生成多版口播文案。
    store 字段：name, city, category, dishes[], avg_price, sell_points[], goal, group_price?
    """
    name = store.get("name") or "本店"
    city = store.get("city") or "本地"
    category = store.get("category") or "美食"
    dishes = store.get("dishes") or []
    avg = store.get("avg_price") or "适中"
    sells = store.get("sell_points") or []
    goal = store.get("goal") or "拉新到店"
    group_price = store.get("group_price") or ""

    dish_str = _join_dishes(dishes)
    sell_str = _join_sells(sells)
    cta = _cta(goal, name, group_price or None)

    builders = {
        "tancha_fancha": lambda: {
            "style_id": "tancha_fancha",
            "style_name": "探店反差",
            "hook": f"路过{city}这家{category}店，门面不起眼，但我劝你别错过。",
            "body": (
                f"一进去先点{dish_str}，人均大概{avg}。"
                f"老板家的卖点很实在：{sell_str}。"
                f"吃完你会明白，为什么附近人总往这儿钻。"
            ),
            "cta": cta,
        },
        "laoban_zishu": lambda: {
            "style_id": "laoban_zishu",
            "style_name": "老板自述",
            "hook": f"大家好，我是「{name}」的老板，今天跟你们说实话。",
            "body": (
                f"我们主打{dish_str}，人均{avg}左右。"
                f"坚持的就一件事：{sell_str}。"
                f"不做花里胡哨，就想让{city}的朋友吃得踏实。"
            ),
            "cta": cta,
        },
        "jiage_chongji": lambda: {
            "style_id": "jiage_chongji",
            "style_name": "价格冲击",
            "hook": (
                f"人均只要{avg}？在{city}吃{category}还想吃好，听听这个价。"
                if not group_price
                else f"团购只要{group_price}！{city}吃{category}这个价你敢信？"
            ),
            "body": (
                f"「{name}」的{dish_str}是镇店招牌，"
                f"再加一句实话：{sell_str}。"
                f"不是便宜没好货，是真心想让你多来几次。"
            ),
            "cta": cta,
        },
        "tongdian_zhongcao": lambda: {
            "style_id": "tongdian_zhongcao",
            "style_name": "痛点种草",
            "hook": f"在{city}找{category}，是不是总踩雷、排队、味道还一般？",
            "body": (
                f"试试「{name}」。点{dish_str}就对了，人均{avg}。"
                f"为啥推荐：{sell_str}。"
                f"解决你「不知道吃啥、又怕踩雷」的烦恼。"
            ),
            "cta": cta,
        },
        "xuanian_gookou": lambda: {
            "style_id": "xuanian_gookou",
            "style_name": "悬念钩子",
            "hook": f"三个字，劝你来「{name}」——别问为什么，先听我说完。",
            "body": (
                f"秘密就是{dish_str}，再配上{sell_str}。"
                f"人均{avg}，在{city}这个位置，性价比你自己来评。"
                f"吃过的人，基本都会带朋友再来。"
            ),
            "cta": cta,
        },
    }

    order = style_ids or [s["id"] for s in STYLES]
    versions: List[Dict[str, Any]] = []
    for sid in order:
        if sid not in builders:
            continue
        if len(versions) >= n:
            break
        piece = builders[sid]()
        full = f"{piece['hook']}{piece['body']}{piece['cta']}"
        versions.append(
            {
                **piece,
                "full_script": full,
                "source": "template",
            }
        )
    return versions
