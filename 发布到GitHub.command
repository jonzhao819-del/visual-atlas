#!/bin/bash
# 双击：把当前网站提交并推送到 GitHub，Pages 会自动更新。
set -euo pipefail
cd "$(dirname "$0")"
git add -A
git commit -m "更新网站 $(date '+%Y-%m-%d %H:%M')" || true
git push
echo ""
echo "✓ 已推送。GitHub Pages 大约 1 分钟后更新。"
echo "网址：https://jonzhao819-del.github.io/visual-atlas/"
