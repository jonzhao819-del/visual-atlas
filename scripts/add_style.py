#!/usr/bin/env python3
"""往自己的档案里加一条风格。

方式一（推荐）：写一个 entry.json，再跑这个脚本
    python3 scripts/add_style.py path/to/entry.json

entry.json 示例：
{
  "title": "Neon Film Still",
  "titleZh": "霓虹剧照",
  "slug": "neon-film-still",
  "image": "/Users/JON/Downloads/neon.jpg",
  "prompt": "Apply a neon-lit night film still ...",
  "kind": "custom",
  "decade": "2020s",
  "chapter": 5,
  "dating": "2020s 霓虹夜景参考",
  "caption": "一张夜景剧照，青绿色与品红光源对打。",
  "credit": "自己整理 / 参考图来源",
  "tags": ["霓虹", "夜景", "电影感"],
  "body": {"识别": "...", "原理": "...", "怎么试": "..."}
}

方式二：命令行直接给字段
    python3 scripts/add_style.py --title "Neon Film Still" --image ~/Downloads/neon.jpg \
        --prompt "..." --decade 2020s --kind custom

图片会自动缩放到 1100px 宽并转成 webp，存进 images/<slug>.webp。
写完会自动重编 assets/data.js。
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "images")
CUSTOM = os.path.join(ROOT, "data", "custom.json")

BODY_MAP = {
    "识别": "Identify",
    "原理": "Principle",
    "怎么试": "Try it out",
    "例子": "Example",
    "归类": "Classification",
    "identify": "Identify",
    "principle": "Principle",
    "try it out": "Try it out",
    "example": "Example",
    "classification": "Classification",
}


def slugify(text, fallback="custom"):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    if s:
        return s
    return fallback + "-" + datetime.datetime.now().strftime("%y%m%d%H%M%S")


def save_image(src, slug):
    if not src:
        return ""
    if not os.path.isabs(src):
        src = os.path.abspath(os.path.join(os.getcwd(), src))
    if not os.path.exists(src):
        raise SystemExit(f"找不到图片：{src}")
    out = os.path.join(IMG_DIR, slug + ".webp")
    im = Image.open(src).convert("RGB")
    if im.width > 1100:
        im = im.resize((1100, round(im.height * 1100 / im.width)), Image.LANCZOS)
    im.save(out, "WEBP", quality=86, method=4)
    return "images/" + slug + ".webp"


def normalize_body(body):
    if not body:
        return []
    if isinstance(body, dict):
        items = list(body.items())
    else:
        items = [(b.get("label"), b.get("text")) for b in body if isinstance(b, dict)]
    out = []
    for label, text in items:
        if not text:
            continue
        key = BODY_MAP.get(str(label).strip(), BODY_MAP.get(str(label).strip().lower(), label))
        out.append({"label": key, "text": str(text).strip()})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entry", nargs="?", help="entry.json 路径")
    ap.add_argument("--title")
    ap.add_argument("--title-zh", dest="title_zh")
    ap.add_argument("--slug")
    ap.add_argument("--image")
    ap.add_argument("--prompt")
    ap.add_argument("--kind", default="custom", choices=["custom", "historical", "digital"])
    ap.add_argument("--decade")
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--dating")
    ap.add_argument("--caption")
    ap.add_argument("--credit")
    ap.add_argument("--source-url", dest="source_url")
    ap.add_argument("--tags", help="英文逗号分隔")
    args = ap.parse_args()

    data = {}
    if args.entry:
        with open(args.entry, encoding="utf-8") as f:
            data = json.load(f)

    def pick(key, default=None):
        val = getattr(args, key.replace("-", "_"), None)
        return val if val not in (None, "") else data.get(key, default)

    title = pick("title")
    if not title:
        raise SystemExit("至少要给一个 --title 或 entry.json 里的 title")

    slug = slugify(pick("slug") or title)
    image = save_image(pick("image"), slug) if pick("image") else data.get("image", "")
    if image:
        from make_thumbs import make_one
        thumb_dir = os.path.join(IMG_DIR, "thumbs")
        os.makedirs(thumb_dir, exist_ok=True)
        try:
            make_one(os.path.join(ROOT, image), os.path.join(thumb_dir, os.path.basename(image)))
        except Exception as exc:  # noqa: BLE001
            print("缩略图生成失败，卡片会退回原图：", exc)

    tags = data.get("tags") or []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    record = {
        "slug": slug,
        "title": title,
        "titleZh": pick("title_zh") or data.get("titleZh") or "",
        "name": data.get("name") or title,
        "kind": pick("kind", "custom"),
        "decade": pick("decade"),
        "chapter": pick("chapter") if pick("chapter") is not None else None,
        "number": None,
        "era": pick("decade"),
        "dating": pick("dating") or "自建条目",
        "short": data.get("short") or title,
        "caption": pick("caption") or "",
        "credit": pick("credit") or "",
        "sourceUrl": pick("source_url") or "",
        "image": image,
        "imageRemote": "",
        "body": normalize_body(data.get("body")),
        "context": data.get("context") or [],
        "distinction": data.get("distinction") or "",
        "aftermath": data.get("aftermath") or "",
        "funFact": data.get("funFact") or "",
        "highlights": data.get("highlights") or tags,
        "margin": data.get("margin") or [],
        "sources": data.get("sources") or [],
        "gallery": [],
        "prompt": pick("prompt") or "",
        "article": data.get("article") or "",
        "custom": True,
        "added": datetime.date.today().isoformat(),
    }

    store = {"effects": []}
    if os.path.exists(CUSTOM):
        with open(CUSTOM, encoding="utf-8") as f:
            store = json.load(f)
    effects = [e for e in store.get("effects", []) if e.get("slug") != slug]
    effects.append(record)
    store["effects"] = effects
    with open(CUSTOM, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=1)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build_data
    build_data.main()
    print(f"已加入：{title}（{slug}）")


if __name__ == "__main__":
    main()
