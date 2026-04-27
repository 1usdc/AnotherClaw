#!/bin/bash
# 安装 Linux systemd 开机自启：等价于在仓库根执行 `just start-d`（停止时 `just close`）
# Install systemd unit so boot runs `just start-d` from repo root (stop: `just close`).
#
# 用法 / Usage:
#   sudo bash scripts/linux/install-systemd-autostart.sh
#   ANOTHERCLAW_SYSTEMD_ROOT=/opt/AnotherClaw sudo -E bash scripts/linux/install-systemd-autostart.sh
#   ANOTHERCLAW_SYSTEMD_USER=deploy ANOTHERCLAW_SYSTEMD_HOME=/home/deploy sudo -E bash ...
#
# 依赖：已安装 `just`，仓库已 pack；路径与 PATH 与手动 `just start-d` 一致即可。
# Requires: `just` on PATH when the service runs; repo packed like manual start-d.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE="$SCRIPT_DIR/anotherclaw-backend.service.in"
UNIT_NAME="${ANOTHERCLAW_SYSTEMD_UNIT_NAME:-anotherclaw-backend.service}"
UNIT_PATH="/etc/systemd/system/$UNIT_NAME"

INSTALL_ROOT="${ANOTHERCLAW_SYSTEMD_ROOT:-/root/AnotherClaw}"
SVC_USER="${ANOTHERCLAW_SYSTEMD_USER:-root}"
SVC_GROUP="${ANOTHERCLAW_SYSTEMD_GROUP:-$(id -gn "$SVC_USER" 2>/dev/null || echo root)}"
if [ -n "${ANOTHERCLAW_SYSTEMD_HOME:-}" ]; then
  SVC_HOME="$ANOTHERCLAW_SYSTEMD_HOME"
elif [ "$SVC_USER" = root ]; then
  SVC_HOME=/root
else
  SVC_HOME="/home/$SVC_USER"
fi
# 追加到单元内 PATH（逗号分隔会写入 Environment=PATH= 的尾部）
EXTRA_PATH="${ANOTHERCLAW_SYSTEMD_EXTRA_PATH:-$SVC_HOME/.cargo/bin:$SVC_HOME/.local/bin}"

if [ ! -f "$TEMPLATE" ]; then
  echo "错误: 未找到模板: $TEMPLATE"
  exit 1
fi

if [ ! -d "$INSTALL_ROOT" ]; then
  echo "错误: 仓库根目录不存在: $INSTALL_ROOT"
  echo "请设置 ANOTHERCLAW_SYSTEMD_ROOT 或先部署代码到该路径。"
  exit 1
fi

if [ ! -f "$INSTALL_ROOT/justfile" ]; then
  echo "错误: 未找到 $INSTALL_ROOT/justfile，请确认 INSTALL_ROOT 指向 AnotherClaw 仓库根。"
  exit 1
fi

if [ "$(id -u)" -ne 0 ]; then
  echo "请使用 root 执行本脚本（需要写入 $UNIT_PATH 并 systemctl enable）。"
  echo "示例: sudo bash $0"
  exit 1
fi

_tmp="$(mktemp)"
# shellcheck disable=SC2016
sed \
  -e "s|@INSTALL_ROOT@|${INSTALL_ROOT//\\/\\\\}|g" \
  -e "s|@SVC_USER@|$SVC_USER|g" \
  -e "s|@SVC_GROUP@|$SVC_GROUP|g" \
  -e "s|@SVC_HOME@|${SVC_HOME//\\/\\\\}|g" \
  -e "s|@EXTRA_PATH@|${EXTRA_PATH//\\/\\\\}|g" \
  "$TEMPLATE" >"$_tmp"

install -m0644 "$_tmp" "$UNIT_PATH"
rm -f "$_tmp"

systemctl daemon-reload
systemctl enable "$UNIT_NAME"
echo "已安装并 enable: $UNIT_PATH"
echo "立即启动: systemctl start $UNIT_NAME"
echo "查看状态: systemctl status $UNIT_NAME"
echo "日志（服务边界）: journalctl -u $UNIT_NAME -b"
echo "应用日志: $INSTALL_ROOT/claw-be-py/build/anotherclaw.log（默认布局下）"
