#!/bin/bash
# 双击运行：在电脑上起一个本地服务，手机连同一 Wi-Fi 就能打开。
cd "$(dirname "$0")" || exit 1
PORT=8777

IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
echo ""
echo "  视觉风格参考档案 · 本地服务已启动"
echo "  ─────────────────────────────────"
echo "  电脑上打开：http://localhost:$PORT"
if [ -n "$IP" ]; then
  echo "  手机上打开：http://$IP:$PORT   （手机和电脑要连同一个 Wi-Fi）"
else
  echo "  没检测到局域网 IP：在「系统设置 → Wi-Fi → 详细信息」里看本机 IP，"
  echo "  手机访问 http://你的IP:$PORT"
fi
echo "  ─────────────────────────────────"
echo "  关掉这个终端窗口，或按 Ctrl + C，服务就停了。"
echo ""

python3 -m http.server "$PORT"
