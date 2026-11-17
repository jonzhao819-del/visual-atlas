#!/usr/bin/env python3
"""抓取 atlas.letz.ai 的全部风格数据与预览图，生成本地站点用的 data.js。

用法：
    python3 scripts/fetch_atlas.py            # 抓数据 + 图片 + 生成 data.js
    python3 scripts/fetch_atlas.py --data     # 只抓数据（复用已下载图片）
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

BASE = "https://atlas.letz.ai"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(ROOT, "images")
DATA_DIR = os.path.join(ROOT, "data")
UA = "visual-atlas-local/1.0 (personal reference archive)"


def get(url, retries=3, timeout=40):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.2 * (i + 1))
    raise last


def fetch_catalog():
    items, offset = [], 0
    while True:
        payload = json.loads(get(f"{BASE}/api/public/atlas/catalog?limit=100&offset={offset}"))
        items.extend(payload["effects"])
        if not payload.get("next"):
            break
        offset += 100
    return items


def fetch_effect(item):
    try:
        data = json.loads(get(f"{BASE}/api/public/atlas/effects/{item['slug']}"))
        return item["slug"], data, None
    except Exception as e:  # noqa: BLE001
        return item["slug"], None, str(e)


def image_source(effect):
    src = effect.get("image") or ""
    if not src:
        return None
    if src.startswith("/"):
        return BASE + src
    return src


def save_image(slug, url):
    if not url:
        return None
    out = os.path.join(IMG_DIR, slug + ".webp")
    if os.path.exists(out) and os.path.getsize(out) > 2000:
        return f"images/{slug}.webp"
    raw = get(url)
    try:
        im = Image.open(io.BytesIO(raw))
    except Exception:  # noqa: BLE001
        # 有的源文件是 gif/svg，直接跳过
        return None
    im = im.convert("RGB")
    if im.width > 1100:
        im = im.resize((1100, round(im.height * 1100 / im.width)), Image.LANCZOS)
    im.save(out, "WEBP", quality=84, method=4)
    return f"images/{slug}.webp"


def norm_text(t):
    return (t or "").strip()


def build_record(item, data, local_image):
    eff = data["effect"]
    body = []
    for b in eff.get("body") or []:
        if b.get("label") and b.get("text"):
            body.append({"label": norm_text(b["label"]), "text": norm_text(b["text"])})
    sources = []
    for s in eff.get("sources") or []:
        if s.get("url"):
            sources.append({"label": norm_text(s.get("label")) or s["url"], "url": s["url"]})
    margin = []
    for m in eff.get("margin") or []:
        if m.get("term") and m.get("note"):
            margin.append({"term": norm_text(m["term"]), "note": norm_text(m["note"])})
    gallery = []
    for g in (data.get("gallery") or [])[:8]:
        if g.get("src"):
            gallery.append({
                "src": g["src"],
                "page": g.get("page") or "",
                "title": norm_text(g.get("title")),
                "artist": norm_text(g.get("artist")),
                "license": norm_text(g.get("license")),
            })
    return {
        "slug": item["slug"],
        "title": norm_text(eff.get("title") or eff.get("name") or item["title"]),
        "name": norm_text(eff.get("name") or item["title"]),
        "kind": item.get("kind") or eff.get("kind"),
        "decade": item.get("decade") or eff.get("decade"),
        "chapter": item.get("chapter") if item.get("chapter") is not None else eff.get("chapter"),
        "number": eff.get("number") or item.get("number"),
        "slide": eff.get("slide"),
        "era": item.get("era"),
        "dating": norm_text(eff.get("dating")),
        "short": norm_text(eff.get("short")),
        "caption": norm_text(eff.get("caption")),
        "credit": norm_text(eff.get("credit")),
        "sourceUrl": eff.get("sourceUrl") or "",
        "image": local_image or "",
        "imageRemote": image_source(eff) or "",
        "body": body,
        "context": [norm_text(c) for c in (eff.get("context") or []) if c],
        "distinction": norm_text(eff.get("distinction")),
        "aftermath": norm_text(eff.get("aftermath")),
        "funFact": norm_text(eff.get("funFact")),
        "highlights": [norm_text(h) for h in (eff.get("highlights") or []) if h],
        "margin": margin,
        "sources": sources,
        "gallery": gallery,
        "prompt": norm_text(data.get("prompt")),
        "article": BASE + (data.get("article") or f"/effect/{item['slug']}"),
        "atlasTitle": norm_text(eff.get("title")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", action="store_true", help="跳过图片下载")
    args = ap.parse_args()
    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    catalog = fetch_catalog()
    print(f"catalog: {len(catalog)} effects")

    results = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_effect, it): it for it in catalog}
        for i, fut in enumerate(as_completed(futs), 1):
            slug, data, err = fut.result()
            if err:
                print("FAIL", slug, err, file=sys.stderr)
            else:
                results[slug] = data
            if i % 50 == 0:
                print(f"  fetched {i}/{len(catalog)}")
    print(f"fetched {len(results)} effect payloads")

    def do_image(item):
        data = results.get(item["slug"])
        if not data or args.data:
            return item["slug"], None
        try:
            return item["slug"], save_image(item["slug"], image_source(data["effect"]))
        except Exception as e:  # noqa: BLE001
            print("IMG FAIL", item["slug"], e, file=sys.stderr)
            return item["slug"], None

    images = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, fut in enumerate(as_completed([ex.submit(do_image, it) for it in catalog]), 1):
            slug, path = fut.result()
            images[slug] = path
            if i % 50 == 0:
                print(f"  images {i}/{len(catalog)}")

    records = []
    for it in catalog:
        data = results.get(it["slug"])
        if not data:
            continue
        records.append(build_record(it, data, images.get(it["slug"])))

    with open(os.path.join(DATA_DIR, "atlas.json"), "w", encoding="utf-8") as f:
        json.dump({"effects": records}, f, ensure_ascii=False, indent=1)

    missing = [r["slug"] for r in records if not r["image"]]
    print(f"records: {len(records)}, images: {len(records) - len(missing)}, missing images: {len(missing)}")
    if missing:
        print("missing:", ", ".join(missing[:20]))

    # 重新编译站点数据（含自建条目）
    import build_data
    build_data.main()


if __name__ == "__main__":
    main()
