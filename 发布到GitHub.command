#!/bin/bash
# 双击：生成缩略图、重编数据、通过 GitHub API 发布，Pages 自动更新。
# 不走 git push（这台机器访问 github.com:443 经常超时）。
set -euo pipefail
cd "$(dirname "$0")"
python3 scripts/make_thumbs.py
python3 scripts/build_data.py
python3 scripts/publish_github.py "更新网站 $(date '+%Y-%m-%d %H:%M')"
echo ""
echo "✓ 完成。约 1 分钟后刷新：https://jonzhao819-del.github.io/visual-atlas/"
