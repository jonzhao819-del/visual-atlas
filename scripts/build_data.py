#!/usr/bin/env python3
"""把 data/atlas.json + data/custom.json 编译成站点用的 assets/data.js。

data.js 用 <script> 载入（不是 fetch），这样直接双击 index.html、手机本地打开都能用。
"""
import datetime
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAPTERS = {
    1: ("Edge & Features", "边缘与特征"),
    2: ("Masks & Control", "蒙版与控制"),
    3: ("Color & Quantization", "色彩与量化"),
    4: ("Print & Dither", "印刷与抖动"),
    5: ("Video & Glitch", "视频与故障"),
    6: ("Space & Optics", "空间与光学"),
    7: ("Filters & Motion", "滤镜与运动"),
    8: ("AI Pipelines", "AI 管线"),
}


def load(name, default):
    path = os.path.join(ROOT, "data", name)
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    base = load("atlas.json", {"effects": []})
    custom = load("custom.json", {"effects": []})
    titles_zh = load("titles-zh.json", {})
    generated = (base.get("meta") or {}).get("generated") or datetime.date.today().isoformat()
    effects = base.get("effects", []) + custom.get("effects", [])

    # 统一编号：按列表顺序给每个条目一个稳定编号（原站的 slide 有缺号，不直观）
    for i, e in enumerate(effects, 1):
        e["plate"] = i
        e.setdefault("custom", False)
    for e in effects:
        if not e.get("titleZh"):
            e["titleZh"] = titles_zh.get(e.get("slug"), "")
        img = e.get("image") or ""
        thumb = "images/thumbs/" + os.path.basename(img) if img else ""
        e["thumb"] = thumb if thumb and os.path.exists(os.path.join(ROOT, thumb)) else img
    for e in custom.get("effects", []):
        e["custom"] = True

    counts = {"historical": 0, "digital": 0}
    for e in effects:
        if e.get("kind") in counts:
            counts[e["kind"]] += 1

    meta = {
        "source": "https://atlas.letz.ai",
        "title": "Atlas of Visual Effects",
        "count": len(effects),
        "generated": generated,
        "historical": counts["historical"],
        "digital": counts["digital"],
        "chapters": [
            {"chapter": k, "en": v[0], "zh": v[1],
             "count": sum(1 for e in effects if e.get("chapter") == k)}
            for k, v in CHAPTERS.items()
        ],
    }

    out = os.path.join(ROOT, "assets", "data.js")
    with open(out, "w", encoding="utf-8") as f:
        f.write("/* 自动生成：scripts/build_data.py。抓取内容请改 data/atlas.json，自建内容请改 data/custom.json。 */\n")
        f.write("window.ATLAS_META = ")
        json.dump(meta, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\nwindow.ATLAS_DATA = ")
        json.dump(effects, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"wrote {out}: {len(effects)} effects ({counts['historical']} historical / {counts['digital']} digital)")


if __name__ == "__main__":
    main()
