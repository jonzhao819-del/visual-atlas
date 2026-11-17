#!/usr/bin/env python3
"""生成可直接上传到静态托管的 dist/ 目录。

用法：
    python3 scripts/build_dist.py

dist/ 里只有网站运行需要的文件：
    index.html
    assets/styles.css  assets/app.js  assets/data.js
    images/*.webp
    robots.txt

上传时把 dist 里的**内容**（不是 dist 文件夹本身）放到托管服务的根目录。
"""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

KEEP_ASSETS = ("styles.css", "app.js", "data.js")


def main():
    if os.path.abspath(DIST) != os.path.join(os.path.abspath(ROOT), "dist"):
        raise SystemExit("dist 路径异常，停止")
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(os.path.join(DIST, "assets"))
    os.makedirs(os.path.join(DIST, "images"))

    shutil.copy2(os.path.join(ROOT, "index.html"), os.path.join(DIST, "index.html"))
    for name in KEEP_ASSETS:
        shutil.copy2(os.path.join(ROOT, "assets", name), os.path.join(DIST, "assets", name))

    src_img = os.path.join(ROOT, "images")
    n = 0
    for name in os.listdir(src_img):
        if name.lower().endswith(".webp"):
            shutil.copy2(os.path.join(src_img, name), os.path.join(DIST, "images", name))
            n += 1
    thumbs = os.path.join(src_img, "thumbs")
    if os.path.isdir(thumbs):
        os.makedirs(os.path.join(DIST, "images", "thumbs"), exist_ok=True)
        for name in os.listdir(thumbs):
            if name.lower().endswith(".webp"):
                shutil.copy2(os.path.join(thumbs, name), os.path.join(DIST, "images", "thumbs", name))

    with open(os.path.join(DIST, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nDisallow: /\n")

    # GitHub Pages：跳过 Jekyll
    with open(os.path.join(DIST, ".nojekyll"), "w", encoding="utf-8") as f:
        f.write("")

    size = 0
    files = 0
    for base, _, names in os.walk(DIST):
        for name in names:
            size += os.path.getsize(os.path.join(base, name))
            files += 1
    print(f"dist/ 已生成：{files} 个文件，{size / 1024 / 1024:.1f} MB，{n} 张图")
    print("上传时拖 dist 文件夹里的内容，或整个 dist 文件夹（看托管服务的提示）。")


if __name__ == "__main__":
    main()
