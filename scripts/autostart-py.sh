#!/usr/bin/env bash
# Linux systemd 自启动管理脚本（开启 / 关闭 / 状态）。
# 用法：
#   bash scripts/autostart-py.sh start [--user <username>] [--service <name>]
#   bash scripts/autostart-py.sh close [--service <name>]
#   bash scripts/autostart-py.sh status [--service <name>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ACTION="${1:-}"
if [ -z "$ACTION" ]; then
  echo "缺少动作参数。可用：start | close | status"
  exit 1
fi
shift || true

SERVICE_NAME="anotherclaw"
RUN_USER="${SUDO_USER:-${USER:-}}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --service)
      SERVICE_NAME="${2:-}"
      shift 2
      ;;
    --user)
      RUN_USER="${2:-}"
      shift 2
      ;;
    *)
      echo "未知参数: $1"
      exit 1
      ;;
  esac
done

if [ "$(uname -s)" != "Linux" ]; then
  echo "该脚本仅支持 Linux。"
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "未检测到 systemctl，当前系统可能未使用 systemd。"
  exit 1
fi

if [ -z "$SERVICE_NAME" ]; then
  echo "--service 不能为空。"
  exit 1
fi

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

ensure_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "需要 root 权限执行：$*"
    exit 1
  fi
}

start_service() {
  if [ -z "$RUN_USER" ]; then
    echo "未能识别运行用户，请用 --user 指定（例如 --user $USER）。"
    exit 1
  fi

  local unit_file
  unit_file="$(mktemp)"
  cat >"$unit_file" <<EOF
[Unit]
Description=AnotherClaw Backend Service
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${ROOT}
Environment=ANOTHERCLAW_NO_SUDO=1
ExecStart=/usr/bin/env bash ${ROOT}/scripts/start-py.sh --py --daemon
Restart=always
RestartSec=3
# 不写 append 到 claw-be-py/：该目录在首次 pack 前可能不存在，会导致 209/STDOUT。
# 默认由 journald 收集标准输出；查看：journalctl -u anotherclaw -f

[Install]
WantedBy=multi-user.target
EOF

  ensure_root install -d /etc/systemd/system
  ensure_root cp "$unit_file" "$SERVICE_FILE"
  rm -f "$unit_file"

  ensure_root systemctl daemon-reload
  ensure_root systemctl enable "$SERVICE_NAME"
  ensure_root systemctl restart "$SERVICE_NAME"

  echo "已开启开机自启动并启动服务: $SERVICE_NAME"
  echo "查看状态: sudo systemctl status $SERVICE_NAME --no-pager"
  echo "查看日志: sudo journalctl -u $SERVICE_NAME -f"
}

close_service() {
  if ensure_root test -f "$SERVICE_FILE"; then
    ensure_root systemctl disable --now "$SERVICE_NAME" || true
    ensure_root rm -f "$SERVICE_FILE"
    ensure_root systemctl daemon-reload
    echo "已关闭开机自启动并移除服务: $SERVICE_NAME"
  else
    echo "服务文件不存在: $SERVICE_FILE"
  fi
}

status_service() {
  ensure_root systemctl status "$SERVICE_NAME" --no-pager || true
}

case "$ACTION" in
  start)
    start_service
    ;;
  close)
    close_service
    ;;
  status)
    status_service
    ;;
  *)
    echo "不支持的动作: $ACTION（可用：start | close | status）"
    exit 1
    ;;
esac
