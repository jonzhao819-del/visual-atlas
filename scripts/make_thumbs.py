#!/usr/bin/env python3
"""给网格卡片生成小图：images/thumbs/<同名>.webp（宽 640，质量 72）。

详情页仍然用 images/ 里的原图；卡片用小图，首屏快很多。
可重复运行，已存在且比原图新的小图会跳过。
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "images")
THUMBS = os.path.join(IMG, "thumbs")
WIDTH = 640
QUALITY = 72


def make_one(src, dst):
    im = Image.open(src).convert("RGB")
    if im.width > WIDTH:
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
    im.save(dst, "WEBP", quality=QUALITY, method=6)


def main():
    os.makedirs(THUMBS, exist_ok=True)
    names = [n for n in os.listdir(IMG) if n.lower().endswith(".webp")]
    made = 0
    for i, name in enumerate(sorted(names), 1):
        src = os.path.join(IMG, name)
        dst = os.path.join(THUMBS, name)
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            continue
        make_one(src, dst)
        made += 1
        if made % 50 == 0:
            print(f"  thumbnails {made}")
    size = sum(os.path.getsize(os.path.join(THUMBS, n)) for n in os.listdir(THUMBS))
    print(f"thumbnails: {len(names)} files, {len(names)} checked, {made} generated, {size/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
