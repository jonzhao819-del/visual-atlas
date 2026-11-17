#!/usr/bin/env python3
"""把本地网站发布到 GitHub 仓库（走 GitHub API，不依赖 git push）。

用法：
    python3 scripts/publish_github.py "更新说明"
    python3 scripts/publish_github.py --dry-run

为什么不用 git push：这台机器访问 github.com:443 经常超时，
但 api.github.com 可以正常访问。这个脚本只上传有变化的文件，
会自动生成新的 tree / commit，然后 GitHub Pages 自动发布。
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

OWNER = "jonzhao819-del"
REPO = "visual-atlas"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUDE_DIRS = {".git", "dist", "node_modules", "__pycache__"}
API = f"https://api.github.com/repos/{OWNER}/{REPO}"


def gh_bin():
    found = shutil.which("gh")
    if found:
        return found
    for p in (
        "/opt/homebrew/bin/gh",
        "/usr/local/bin/gh",
        os.path.expanduser("~/.local/bin/gh"),
    ):
        if os.path.exists(p):
            return p
    raise SystemExit("找不到 gh（GitHub CLI）。请先安装或登录 GitHub。")


GH = gh_bin()
TOKEN = subprocess.check_output([GH, "auth", "token"], text=True).strip()


def api(method, path, data=None, retries=8):
    url = path if path.startswith("http") else API + path
    body = json.dumps(data).encode() if data is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(
            url, data=body, method=method,
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "visual-atlas-publish",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            if e.code in (403, 429) and attempt < retries - 1:
                wait = int(e.headers.get("Retry-After") or min(60, 2 ** (attempt + 1)))
                print(f"  触发限流，等 {wait}s 重试…", flush=True)
                time.sleep(wait); continue
            if e.code >= 500 and attempt < retries - 1:
                time.sleep(2 ** attempt); continue
            raise RuntimeError(f"{method} {path} -> {e.code}: {raw[:400]}")
        except (urllib.error.URLError, ssl.SSLError, TimeoutError, ConnectionError) as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt); continue
            raise RuntimeError(f"{method} {path} 网络错误: {e}")
    raise RuntimeError("unreachable")


def blob_sha(path):
    data = open(path, "rb").read()
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest(), data


def local_files():
    out = []
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in names:
            if name == ".DS_Store":
                continue
            full = os.path.join(base, name)
            rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
            sha, data = blob_sha(full)
            mode = "100755" if name.endswith(".command") else "100644"
            out.append({"path": rel, "sha": sha, "mode": mode, "full": full, "data": data})
    out.sort(key=lambda x: x["path"])
    return out


def build_tree(entries, label, base=None):
    """entries: [{path,mode,type,sha}]；超过 100 个分批，用 base_tree 串起来。"""
    if not entries:
        return base
    if len(entries) <= 100:
        payload = {"tree": entries}
        if base:
            payload["base_tree"] = base
        return api("POST", "/git/trees", payload)["sha"]
    sha = base
    for i in range(0, len(entries), 80):
        payload = {"tree": entries[i:i + 80]}
        if sha:
            payload["base_tree"] = sha
        sha = api("POST", "/git/trees", payload)["sha"]
        print(f"  {label} {min(i + 80, len(entries))}/{len(entries)}", flush=True)
        time.sleep(0.15)
    return sha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("message", nargs="?", default="更新网站")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    head = api("GET", "/git/ref/heads/main")["object"]["sha"]
    root_sha = api("GET", f"/git/commits/{head}")["tree"]["sha"]
    remote = api("GET", f"/git/trees/{root_sha}?recursive=1")["tree"]
    remote_blobs = {e["path"]: e["sha"] for e in remote if e["type"] == "blob"}
    remote_trees = {e["path"]: e["sha"] for e in remote if e["type"] == "tree"}
    root_entries = {e["path"]: e for e in api("GET", f"/git/trees/{root_sha}")["tree"]}

    files = local_files()
    changed = [f for f in files if remote_blobs.get(f["path"]) != f["sha"]]
    print(f"本地 {len(files)} 个文件，需要上传 {len(changed)} 个", flush=True)
    if not changed:
        print("已经是最新，无需发布。")
        return
    if args.dry_run:
        for f in changed[:30]:
            print("  ", f["path"])
        if len(changed) > 30:
            print("   …")
        return

    def upload(f):
        res = api("POST", "/git/blobs", {
            "content": base64.b64encode(f["data"]).decode(),
            "encoding": "base64",
        })
        f["new_sha"] = res["sha"]
        return f

    # 4 路并发；遇到 403/429 会自动退避重试
    with ThreadPoolExecutor(max_workers=4) as ex:
        for i, _ in enumerate(ex.map(upload, changed), 1):
            if i % 50 == 0 or i == len(changed):
                print(f"  上传 {i}/{len(changed)}", flush=True)

    local_map = {f["path"]: f for f in files}

    def entries_for_prefix(prefix):
        out = []
        for f in files:
            if f["path"].startswith(prefix):
                out.append({
                    "path": f["path"][len(prefix):],
                    "mode": f["mode"],
                    "type": "blob",
                    "sha": f.get("new_sha", f["sha"]),
                })
        return out

    def changed_under(prefix):
        return any(f["path"].startswith(prefix) for f in changed)

    tree_updates = []

    for d in ("assets", "data", "scripts", "screenshots"):
        if changed_under(d + "/"):
            sha = build_tree(entries_for_prefix(d + "/"), d)
            tree_updates.append({"path": d, "mode": "040000", "type": "tree", "sha": sha})
            print(f"  {d}: {sha}", flush=True)

    # images：504 张原图 + thumbs 子目录，用 base_tree 增量更新
    images_sha = remote_trees.get("images")
    image_changed = changed_under("images/") and not all(f["path"].startswith("images/thumbs/") for f in changed if f["path"].startswith("images/"))
    thumbs_changed = any(f["path"].startswith("images/thumbs/") for f in changed)
    if images_sha and (image_changed or thumbs_changed):
        updates = []
        thumbs_sha = remote_trees.get("images/thumbs")
        if thumbs_changed:
            thumbs_sha = build_tree(entries_for_prefix("images/thumbs/"), "images/thumbs", base=None)
            print(f"  images/thumbs: {thumbs_sha}", flush=True)
        if thumbs_sha:
            updates.append({"path": "thumbs", "mode": "040000", "type": "tree", "sha": thumbs_sha})
        for f in changed:
            if f["path"].startswith("images/") and not f["path"].startswith("images/thumbs/"):
                updates.append({
                    "path": f["path"][len("images/"):],
                    "mode": f["mode"], "type": "blob", "sha": f["new_sha"],
                })
        new_images = api("POST", "/git/trees", {"base_tree": images_sha, "tree": updates})["sha"]
        tree_updates.append({"path": "images", "mode": "040000", "type": "tree", "sha": new_images})
        print(f"  images: {new_images}", flush=True)

    for f in changed:
        if "/" not in f["path"]:
            tree_updates.append({
                "path": f["path"], "mode": f["mode"], "type": "blob", "sha": f["new_sha"],
            })

    if not tree_updates:
        print("只有文件内容变化但没有对应目录更新，停止。")
        return

    new_root = api("POST", "/git/trees", {"base_tree": root_sha, "tree": tree_updates})["sha"]
    print("root tree:", new_root, flush=True)
    commit = api("POST", "/git/commits", {
        "message": args.message,
        "tree": new_root,
        "parents": [head],
    })
    print("commit:", commit["sha"], flush=True)
    api("PATCH", "/git/refs/heads/main", {"sha": commit["sha"], "force": True})
    print("✓ 已发布。GitHub Pages 约 1 分钟后更新。")
    print("https://jonzhao819-del.github.io/visual-atlas/")


if __name__ == "__main__":
    main()
