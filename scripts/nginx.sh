#!/usr/bin/env bash
# Nginx 一键 setup：缺则装、备份并替换 default、写入 default.conf（80 反代）、enable+restart。
# Usage:
#   bash scripts/nginx.sh [setup]
#   NGINX_UPSTREAM_PORT=8080 bash scripts/nginx.sh
#   NGINX_SETUP_FORCE=1 bash scripts/nginx.sh   # 强制重写
#   just nginx-setup

set -euo pipefail

CONF_NAME="default.conf"
SETUP_MARKER="/etc/nginx/.anotherclaw-nginx-setup"

require_linux() {
  if [ "$(uname -s)" != "Linux" ]; then
    echo "仅支持 Linux。"
    exit 1
  fi
}

ensure_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "需要 root 权限（sudo 或以 root 运行）。"
    exit 1
  fi
}

run_pkg() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "需要 root 权限安装 nginx（使用 sudo 或以 root 运行）。"
    exit 1
  fi
}

ensure_nginx_installed() {
  if command -v nginx >/dev/null 2>&1; then
    echo "nginx 已安装: $(command -v nginx)"
    nginx -v 2>&1 || true
    return 0
  fi

  if command -v apt-get >/dev/null 2>&1; then
    run_pkg apt-get update -qq
    run_pkg apt-get install -y -qq nginx
  elif command -v dnf >/dev/null 2>&1; then
    run_pkg dnf install -y nginx
  elif command -v yum >/dev/null 2>&1; then
    run_pkg yum install -y nginx
  elif command -v apk >/dev/null 2>&1; then
    run_pkg apk add --no-cache nginx
  else
    echo "未识别包管理器（需要 apt-get / dnf / yum / apk）。请手动安装 nginx。"
    exit 1
  fi

  echo "nginx 安装完成: $(command -v nginx)"
  nginx -v 2>&1 || true
}

write_reverse_proxy_to() {
  local target="$1"
  local UPSTREAM_PORT="$2"
  ensure_root tee "$target" >/dev/null <<EOF
# AnotherClaw：HTTP 80 反代到本机 ${UPSTREAM_PORT}（由 scripts/nginx.sh 写入 default.conf）
server {
    listen 80;
    listen [::]:80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:${UPSTREAM_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }
}
EOF
}

deploy_reverse_proxy_conf() {
  local UPSTREAM_PORT="$1"

  if [ -d /etc/nginx/sites-available ] && [ -d /etc/nginx/sites-enabled ]; then
    write_reverse_proxy_to "/etc/nginx/sites-available/${CONF_NAME}" "$UPSTREAM_PORT"
    ensure_root ln -sf "/etc/nginx/sites-available/${CONF_NAME}" "/etc/nginx/sites-enabled/${CONF_NAME}"
    echo "已写入 /etc/nginx/sites-available/${CONF_NAME} 并已启用。"
  elif [ -d /etc/nginx/http.d ]; then
    write_reverse_proxy_to "/etc/nginx/http.d/${CONF_NAME}" "$UPSTREAM_PORT"
    echo "已写入 /etc/nginx/http.d/${CONF_NAME}。"
  elif [ -d /etc/nginx/conf.d ]; then
    write_reverse_proxy_to "/etc/nginx/conf.d/${CONF_NAME}" "$UPSTREAM_PORT"
    echo "已写入 /etc/nginx/conf.d/${CONF_NAME}。"
  else
    echo "未找到 nginx 配置目录（sites-available / http.d / conf.d）。请手动配置。"
    exit 1
  fi
}

disable_default_site() {
  # Debian/Ubuntu：旧默认站点名为 default（无扩展名）
  if [ -L /etc/nginx/sites-enabled/default ]; then
    ensure_root rm -f /etc/nginx/sites-enabled/default
    echo "已移除 /etc/nginx/sites-enabled/default（旧默认站点）。"
  fi
  # 已有 default.conf 时先备份再交由 deploy 覆盖（RPM）
  if [ -f /etc/nginx/conf.d/default.conf ]; then
    ensure_root mv /etc/nginx/conf.d/default.conf "/etc/nginx/conf.d/default.conf.bak.before-anotherclaw"
    echo "已将原 /etc/nginx/conf.d/default.conf 备份为 default.conf.bak.before-anotherclaw。"
  fi
  # Alpine
  if [ -f /etc/nginx/http.d/default.conf ]; then
    ensure_root mv /etc/nginx/http.d/default.conf "/etc/nginx/http.d/default.conf.bak.before-anotherclaw"
    echo "已将原 /etc/nginx/http.d/default.conf 备份为 default.conf.bak.before-anotherclaw。"
  fi
}

nginx_conf_present() {
  [ -f "/etc/nginx/sites-available/${CONF_NAME}" ] || [ -f "/etc/nginx/conf.d/${CONF_NAME}" ] || [ -f "/etc/nginx/http.d/${CONF_NAME}" ]
}

already_setup_complete() {
  local UPSTREAM_PORT="$1"
  [ -z "${NGINX_SETUP_FORCE:-}" ] || return 1
  [ -f "$SETUP_MARKER" ] || return 1
  local saved
  saved="$(tr -d '\r\n' < "$SETUP_MARKER" 2>/dev/null || true)"
  [ "$saved" = "$UPSTREAM_PORT" ] || return 1
  nginx_conf_present || return 1
  command -v nginx >/dev/null 2>&1 || return 1
  if command -v systemctl >/dev/null 2>&1; then
    ensure_root systemctl is-enabled nginx >/dev/null 2>&1 || return 1
    ensure_root systemctl is-active nginx >/dev/null 2>&1 || return 1
  elif command -v rc-service >/dev/null 2>&1; then
    ensure_root rc-service nginx status >/dev/null 2>&1 || return 1
  else
    pgrep -x nginx >/dev/null 2>&1 || return 1
  fi
  return 0
}

enable_and_restart_nginx() {
  if command -v systemctl >/dev/null 2>&1; then
    ensure_root systemctl enable nginx 2>/dev/null || true
    ensure_root systemctl restart nginx
    echo "已执行: systemctl enable nginx && systemctl restart nginx"
    return 0
  fi
  if command -v rc-service >/dev/null 2>&1; then
    ensure_root rc-update add nginx default 2>/dev/null || true
    ensure_root rc-service nginx restart
    echo "已执行: rc-update add nginx + rc-service nginx restart"
    return 0
  fi
  if ensure_root service nginx restart 2>/dev/null; then
    echo "已执行: service nginx restart"
    return 0
  fi
  echo "无法 enable/restart nginx，请手动检查。"
  exit 1
}

cmd_setup() {
  require_linux
  local UPSTREAM_PORT="${NGINX_UPSTREAM_PORT:-8765}"

  ensure_nginx_installed

  if already_setup_complete "$UPSTREAM_PORT"; then
    echo "nginx 反代已按端口 ${UPSTREAM_PORT} 配置完成（default.conf），服务已启用并在运行，跳过。"
    exit 0
  fi

  echo "=== 备份 default、写入 default.conf、校验并重启 ==="
  disable_default_site
  deploy_reverse_proxy_conf "$UPSTREAM_PORT"
  ensure_root nginx -t
  printf '%s\n' "$UPSTREAM_PORT" | ensure_root tee "$SETUP_MARKER" >/dev/null
  enable_and_restart_nginx
  echo "反代: http://<服务器IP>/ -> http://127.0.0.1:${UPSTREAM_PORT}/"
  echo "标记文件: ${SETUP_MARKER}（改端口可设 NGINX_UPSTREAM_PORT 或 NGINX_SETUP_FORCE=1 强制重写）"
}

usage() {
  echo "用法: bash scripts/nginx.sh [setup]"
  echo "  省略参数时等价于 setup。一键：安装 nginx（若缺）、备份原 default、写入 default.conf（80 反代）、开机自启并重启。"
  echo "  环境变量: NGINX_UPSTREAM_PORT（默认 8765） NGINX_SETUP_FORCE=1（强制重写）"
}

ACTION="${1:-setup}"
case "$ACTION" in
  setup)
    cmd_setup
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  "")
    usage
    exit 1
    ;;
  *)
    echo "未知参数: $ACTION（仅支持 setup，或直接省略参数）"
    usage
    exit 1
    ;;
esac
