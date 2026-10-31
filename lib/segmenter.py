"""按中文语速把口播文案切成 ≤15 秒片段。"""
from __future__ import annotations

import re
from typing import List, Dict


# 中文口播语速约 4–4.5 字/秒；取中间值 4.2
CHARS_PER_SEC = 4.2
MAX_SECONDS = 15.0
MAX_CHARS = int(CHARS_PER_SEC * MAX_SECONDS)  # ≈ 63


def estimate_seconds(text: str, cps: float = CHARS_PER_SEC) -> float:
    """按字数估算秒数（不计标点停顿的粗估）。"""
    # 去掉空白，按字符计
    chars = len(re.sub(r"\s+", "", text))
    if chars == 0:
        return 0.0
    return round(chars / cps, 1)


def _split_sentences(text: str) -> List[str]:
    """按句号/问号/叹号/分号/换行先拆句，再按逗号细拆，尽量不断开词。"""
    text = text.strip()
    if not text:
        return []
    # 保留分隔符
    parts = re.split(r"(?<=[。！？；!?;\n])", text)
    sentences: List[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # 若单句仍超长，再按逗号/顿号拆
        if len(re.sub(r"\s+", "", p)) > MAX_CHARS:
            sub = re.split(r"(?<=[，、,])", p)
            buf = ""
            for s in sub:
                s = s.strip()
                if not s:
                    continue
                candidate = (buf + s).strip()
                if buf and len(re.sub(r"\s+", "", candidate)) > MAX_CHARS:
                    sentences.append(buf)
                    buf = s
                else:
                    buf = candidate
            if buf:
                sentences.append(buf)
        else:
            sentences.append(p)
    return sentences


def segment_script(
    text: str,
    max_seconds: float = MAX_SECONDS,
    cps: float = CHARS_PER_SEC,
) -> List[Dict]:
    """
    把整段文案切成 ≤ max_seconds 的片段。
    返回 [{index, text, chars, seconds}, ...]
    """
    max_chars = int(cps * max_seconds)
    sentences = _split_sentences(text)
    segments: List[Dict] = []
    buf = ""

    def flush():
        nonlocal buf
        if not buf:
            return
        clean = buf.strip()
        chars = len(re.sub(r"\s+", "", clean))
        segments.append(
            {
                "index": len(segments) + 1,
                "text": clean,
                "chars": chars,
                "seconds": estimate_seconds(clean, cps),
            }
        )
        buf = ""

    for sent in sentences:
        candidate = (buf + sent).strip()
        cand_chars = len(re.sub(r"\s+", "", candidate))
        if buf and cand_chars > max_chars:
            flush()
            # 单句仍超长：硬切（尽量在标点处）
            while len(re.sub(r"\s+", "", sent)) > max_chars:
                # 找最靠近 max_chars 的逗号/空格
                cut = max_chars
                window = sent[: cut + 5]
                m = list(re.finditer(r"[，、,\s]", window))
                if m:
                    cut = m[-1].end()
                piece = sent[:cut].strip()
                if piece:
                    chars = len(re.sub(r"\s+", "", piece))
                    segments.append(
                        {
                            "index": len(segments) + 1,
                            "text": piece,
                            "chars": chars,
                            "seconds": estimate_seconds(piece, cps),
                        }
                    )
                sent = sent[cut:].strip()
            buf = sent
        else:
            buf = candidate
    flush()
    return segments
