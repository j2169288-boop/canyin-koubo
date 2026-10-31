"""Grok Imagine Video image-to-video + lip-sync 提示词生成。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


DEFAULT_AVATAR = {
    "appearance_zh": "30岁左右东亚男性，短发干净利落，亲切微笑，五官端正",
    "appearance_en": "East Asian man around 30, neat short hair, friendly smile, clear features",
    "outfit_zh": "深色休闲衬衫，简洁无logo",
    "outfit_en": "dark casual button-up shirt, simple, no logos",
    "scene_zh": "餐厅室内，暖色灯光，背景虚化可见桌面餐品",
    "scene_en": "restaurant interior, warm lighting, softly blurred table with dishes in background",
    "camera_zh": "胸像近景，正面略侧，手机竖拍机位",
    "camera_en": "medium close-up chest-up, slight three-quarter angle, handheld phone vertical framing",
}


def ensure_avatar(avatar: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    base = dict(DEFAULT_AVATAR)
    if avatar:
        base.update({k: v for k, v in avatar.items() if v})
    return base


def build_segment_prompt(
    segment_text: str,
    store: Dict[str, Any],
    avatar: Optional[Dict[str, str]] = None,
    segment_index: int = 1,
) -> Dict[str, str]:
    """
    为单段口播生成英文 i2v+lip-sync prompt + 中文说明。
    9:16 竖屏；固定数字人字段以保持多段一致性。
    """
    av = ensure_avatar(avatar)
    name = store.get("name") or "the restaurant"
    dish_hint = ""
    dishes = store.get("dishes") or []
    if dishes:
        dish_hint = f" Subtle hint of signature dish ({dishes[0]}) on the table behind."

    # 台词做简单转义，避免打断 prompt
    line = segment_text.replace('"', "'").strip()

    prompt_en = (
        f"Image-to-video, vertical 9:16, photorealistic talking-head digital human. "
        f"Subject: {av['appearance_en']}, wearing {av['outfit_en']}. "
        f"Scene: {av['scene_en']}.{dish_hint} "
        f"Camera: {av['camera_en']}, locked framing, mild natural head motion. "
        f"Action: speaking to camera with natural hand gestures, confident and warm. "
        f"Expression: engaging, sincere, slight smile while talking. "
        f"Lip-sync: accurately mouth the Chinese line: \"{line}\". "
        f"Audio: clear Mandarin voiceover matching the lip motion. "
        f"Lighting: warm restaurant practical lights, soft key, no flicker. "
        f"Quality: sharp face, natural skin, no warping, no subtitle burn-in. "
        f"Brand context: promo for {name}. Segment {segment_index}."
    )

    explain_zh = (
        f"【片段{segment_index}】9:16竖屏 · 图生视频+口型同步\n"
        f"人物：{av['appearance_zh']}；服装：{av['outfit_zh']}\n"
        f"场景/机位：{av['scene_zh']}；{av['camera_zh']}\n"
        f"动作/表情：对镜口播，自然手势，真诚微笑\n"
        f"口型同步台词：{line}\n"
        f"光线：餐厅暖光，面部清晰无闪烁\n"
        f"用法：上传店铺数字人定妆图 → Grok Imagine Video（image-to-video + lip-sync）→ 粘贴上方英文 prompt"
    )

    return {
        "prompt_en": prompt_en,
        "explain_zh": explain_zh,
        "line": line,
        "aspect": "9:16",
        "mode": "image-to-video + lip-sync",
    }


def build_prompts_for_version(
    segments: List[Dict[str, Any]],
    store: Dict[str, Any],
    avatar: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    out = []
    for seg in segments:
        p = build_segment_prompt(
            seg["text"], store, avatar=avatar, segment_index=seg.get("index", 1)
        )
        out.append({**seg, "video_prompt": p})
    return out
