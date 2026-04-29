#!/usr/bin/env bash
# Nginx：install 安装 | set 配置 80 反代到本机端口（默认 8765）| restart 重启。
# Usage:
#   bash scripts/nginx.sh install
#   bash scripts/nginx.sh set                      # 可选 NGINX_UPSTREAM_PORT=8080
#   bash scripts/nginx.sh restart
#   just nginx-install / nginx-set / nginx-restart

set -euo pipefail

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

cmd_install() {
  require_linux

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
  echo "常用命令: sudo systemctl enable --now nginx    sudo systemctl status nginx"
}

cmd_restart() {
  require_linux

  if ! command -v nginx >/dev/null 2>&1; then
    echo "未找到 nginx，请先执行: bash scripts/nginx.sh install 或 just nginx-install"
    exit 1
  fi

  if ensure_root systemctl restart nginx 2>/dev/null; then
    echo "已执行: systemctl restart nginx"
  elif command -v rc-service >/dev/null 2>&1 && ensure_root rc-service nginx restart 2>/dev/null; then
    echo "已执行: rc-service nginx restart"
  elif ensure_root service nginx restart 2>/dev/null; then
    echo "已执行: service nginx restart"
  else
    echo "无法通过 systemd/OpenRC/service 重启 nginx，请手动检查。"
    exit 1
  fi
}

cmd_set() {
  require_linux

  local UPSTREAM_PORT="${NGINX_UPSTREAM_PORT:-8765}"
  local CONF_NAME="anotherclaw-reverse-proxy.conf"

  if ! command -v nginx >/dev/null 2>&1; then
    echo "未找到 nginx，请先执行: bash scripts/nginx.sh install 或 just nginx-install"
    exit 1
  fi

  write_conf_to() {
    local target="$1"
    ensure_root tee "$target" >/dev/null <<EOF
# AnotherClaw：HTTP 80 反代到本机 ${UPSTREAM_PORT}（由 scripts/nginx.sh set 生成）
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

  reload_nginx() {
    ensure_root nginx -t
    if command -v systemctl >/dev/null 2>&1 && ensure_root systemctl reload nginx 2>/dev/null; then
      echo "已 reload nginx（systemctl reload）。"
    elif command -v rc-service >/dev/null 2>&1 && ensure_root rc-service nginx reload 2>/dev/null; then
      echo "已 reload nginx（OpenRC）。"
    else
      ensure_root nginx -s reload
      echo "已 reload nginx（nginx -s reload）。"
    fi
  }

  if [ -d /etc/nginx/sites-available ] && [ -d /etc/nginx/sites-enabled ]; then
    write_conf_to "/etc/nginx/sites-available/${CONF_NAME}"
    ensure_root ln -sf "/etc/nginx/sites-available/${CONF_NAME}" "/etc/nginx/sites-enabled/${CONF_NAME}"
    echo "已写入 /etc/nginx/sites-available/${CONF_NAME} 并已启用。"
  elif [ -d /etc/nginx/http.d ]; then
    write_conf_to "/etc/nginx/http.d/${CONF_NAME}"
    echo "已写入 /etc/nginx/http.d/${CONF_NAME}。"
  elif [ -d /etc/nginx/conf.d ]; then
    write_conf_to "/etc/nginx/conf.d/${CONF_NAME}"
    echo "已写入 /etc/nginx/conf.d/${CONF_NAME}。"
  else
    echo "未找到 nginx 配置目录（sites-available / http.d / conf.d）。请手动配置。"
    exit 1
  fi

  reload_nginx
  echo "反代: http://<服务器IP>/ -> http://127.0.0.1:${UPSTREAM_PORT}/"
  echo "若仍打开默认页，可禁用默认站点（如 Debian/Ubuntu 删除 sites-enabled/default 软链）。"
}

usage() {
  echo "用法: bash scripts/nginx.sh install | set | restart"
  echo "  install   安装 nginx（apt/dnf/yum/apk）"
  echo "  set       配置 80 反代到本机端口（默认 8765，可用 NGINX_UPSTREAM_PORT 覆盖）"
  echo "  restart   重启 nginx"
}

ACTION="${1:-}"
case "$ACTION" in
  install)
    cmd_install
    ;;
  set)
    cmd_set
    ;;
  restart)
    cmd_restart
    ;;
  "")
    usage
    exit 1
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    echo "未知子命令: $ACTION"
    usage
    exit 1
    ;;
esac
