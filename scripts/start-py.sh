#!/bin/bash
# 启动后端：安装 podman/uv、创建环境、安装依赖、可选构建前端、在 claw-be-py/build 启动 main.py（须先 just pack）
# 从项目根执行：just start 或 just start-d；仅后端（不构建前端）：just back
# 也可直接调用：bash scripts/start-py.sh [--py] [-d|--daemon] [-b|--backend]
# start-d 若 PID 仍存活会跳过；需无视时可设 ANOTHERCLAW_FORCE_START_D=1
# Linux 非 root 时默认通过 sudo -E 启动 main.py（可设 ANOTHERCLAW_NO_SUDO=1 关闭）

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 用户级工具（uv 等）默认装在此；just 的非登录子 shell 常未继承该路径
export PATH="$HOME/.local/bin${PATH:+:$PATH}"

# 简化版自动识别目录（支持在项目根、claw-be-py、claw-be-py/build 或独立 build 目录下执行）
if [ -d "$PWD/claw-be-py" ]; then
  ROOT="$PWD"
  BACKEND="$ROOT/claw-be-py"
elif [ -f "$PWD/main.py" ] && [ -f "$PWD/pyproject.toml" ]; then
  ROOT="$PWD"
  BACKEND="$ROOT"
else
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  if [ -f "$ROOT/main.py" ] && [ -f "$ROOT/pyproject.toml" ]; then
    BACKEND="$ROOT"
  elif [ -d "$ROOT/claw-be-py" ]; then
    BACKEND="$ROOT/claw-be-py"
  else
    BACKEND="$ROOT/claw-be-py"
  fi
fi

DAEMON=0
BACKEND_ONLY=0
for _arg in "$@"; do
  case "$_arg" in
    -d|--daemon) DAEMON=1 ;;
    -b|--backend) BACKEND_ONLY=1 ;;
  esac
done

if [ ! -d "$BACKEND" ]; then
  echo "错误: backend 目录不存在: $BACKEND"
  echo "请确认从正确的项目根执行（项目根应包含 claw-be-py/ 与 scripts/）"
  exit 1
fi

# daemon：若 anotherclaw-daemon.pid 指向的进程仍存活，跳过后续（避免重复 start-d；与 status-py / close-py 一致）
if [ "$DAEMON" -eq 1 ] && [ -z "${ANOTHERCLAW_FORCE_START_D:-}" ]; then
  _daemon_pidfile="$ROOT/anotherclaw-daemon.pid"
  if [ -f "$_daemon_pidfile" ]; then
    _daemon_pid="$(tr -d ' \n\r\t' <"$_daemon_pidfile" || true)"
    if [ -n "$_daemon_pid" ] && [[ "$_daemon_pid" =~ ^[0-9]+$ ]] && kill -0 "$_daemon_pid" 2>/dev/null; then
      echo "后台已在运行（PID=$_daemon_pid），跳过重复启动。"
      echo "停止请执行: just close；强制再启可设 ANOTHERCLAW_FORCE_START_D=1"
      exit 0
    fi
  fi
fi

# 标准布局：claw-be-py/build/main.py；若当前已在打包目录内（BACKEND 即为 …/build），则为 BACKEND/main.py
if [ -f "$BACKEND/build/main.py" ]; then
  cd "$BACKEND/build"
elif [ -f "$BACKEND/main.py" ] && [ -f "$BACKEND/pyproject.toml" ]; then
  cd "$BACKEND"
else
  echo "未找到打包后的 main.py（已尝试: $BACKEND/build/main.py 与 $BACKEND/main.py），请先执行: just pack"
  exit 1
fi

# ---------- podman ----------
if ! command -v podman >/dev/null 2>&1; then
  echo "未检测到 podman，开始自动安装..."
  if command -v brew >/dev/null 2>&1; then
    brew install podman
  elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq && apt-get install -y -qq podman || true
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y podman 2>/dev/null || true
  elif command -v yum >/dev/null 2>&1; then
    yum install -y podman 2>/dev/null || true
  elif command -v apk >/dev/null 2>&1; then
    apk add --no-cache podman 2>/dev/null || true
  fi
fi

if ! command -v podman >/dev/null 2>&1; then
  echo "未找到 podman，请先手动安装 podman。"
  exit 1
fi

if [ "$(uname -s)" = "Darwin" ]; then
  if ! podman machine inspect >/dev/null 2>&1; then
    echo "初始化 podman machine..."
    podman machine init
  fi
  echo "启动 podman machine..."
  if ! podman machine start >/dev/null 2>&1; then
    if ! podman machine list 2>/dev/null | grep -q "Currently running"; then
      echo "podman machine 启动失败，请手动执行: podman machine start"
      exit 1
    fi
  fi
fi

# ---------- 异步预拉取常用镜像 ----------
_img_python="${ANOTHERCLAW_PODMAN_IMAGE_PYTHON:-docker.io/library/python:3.12}"
_img_node="${ANOTHERCLAW_PODMAN_IMAGE_NODE:-docker.io/library/node:22}"
_img_shell="${ANOTHERCLAW_PODMAN_IMAGE_SHELL:-docker.io/library/bash:5.2}"
_img_go="${ANOTHERCLAW_PODMAN_IMAGE_GO:-docker.io/library/golang:1.22}"
_img_java="${ANOTHERCLAW_PODMAN_IMAGE_JAVA:-docker.io/library/openjdk:21-jdk}"
_img_rust="${ANOTHERCLAW_PODMAN_IMAGE_RUST:-docker.io/library/rust:latest}"
_img_php="${ANOTHERCLAW_PODMAN_IMAGE_PHP:-docker.io/library/php:8.3-cli}"
_img_default="${ANOTHERCLAW_PODMAN_IMAGE:-${_img_shell}}"
for _img in "$_img_python" "$_img_node" "$_img_shell" "$_img_go" "$_img_java" "$_img_rust" "$_img_php" "$_img_default"; do
  [ -z "$_img" ] && continue
  if ! podman image exists "$_img" >/dev/null 2>&1; then
    echo "后台预拉取镜像: $_img"
    (podman pull "$_img" >/dev/null 2>&1 || true) &
  fi
done

# 与 quickstart 一致：首次通过官方脚本安装后把 PATH 写入 ~/.profile 或 ~/.bashrc
persist_user_local_bin_path() {
  [ -n "${HOME:-}" ] || return 0
  local marker="# AnotherClaw: ~/.local/bin (uv)"
  local f
  for f in "${HOME}/.profile" "${HOME}/.bashrc"; do
    [ -f "$f" ] || continue
    grep -Fq "$marker" "$f" 2>/dev/null && return 0
  done
  local target="${HOME}/.profile"
  if [ ! -f "$target" ]; then
    target="${HOME}/.bashrc"
  fi
  if [ ! -f "$target" ]; then
    target="${HOME}/.profile"
    touch "$target" 2>/dev/null || return 0
  fi
  {
    echo ""
    echo "$marker"
    echo 'export PATH="$HOME/.local/bin:$PATH"'
  } >>"$target" 2>/dev/null || return 0
  echo "已将 ~/.local/bin 追加到 $target（重新登录或 source 后全局生效）"
}

# ---------- uv ----------
if ! command -v uv >/dev/null 2>&1; then
  echo "未检测到 uv，开始自动安装..."
  if ! command -v curl >/dev/null 2>&1; then
    echo "未找到 curl，尝试先安装 curl..."
    if command -v apt-get >/dev/null 2>&1; then
      apt-get update -qq && apt-get install -y -qq curl || true
    elif command -v apk >/dev/null 2>&1; then
      apk add --no-cache curl 2>/dev/null || true
    elif command -v dnf >/dev/null 2>&1; then
      dnf install -y curl 2>/dev/null || true
    elif command -v yum >/dev/null 2>&1; then
      yum install -y curl 2>/dev/null || true
    fi
  fi
  if ! command -v curl >/dev/null 2>&1; then
    echo "无法安装 curl，请先在系统中安装 curl 或预装 uv。"
    exit 1
  fi
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin${PATH:+:$PATH}"
  if ! command -v uv >/dev/null 2>&1; then
    echo "uv 安装后仍不可用，请检查 PATH（建议加入 ~/.local/bin）"
    exit 1
  fi
fi
if [ -x "${HOME}/.local/bin/uv" ]; then
  persist_user_local_bin_path
fi

# ---------- venv / 依赖 ----------
if [ ! -x ".venv/bin/python" ]; then
  if [ -d ".venv" ]; then
    echo "检测到 .venv 存在但不可用，使用 --clear 非交互重建..."
    uv venv --clear .venv
  else
    echo "创建虚拟环境 .venv..."
    uv venv .venv
  fi
fi

# sudo 下须用绝对路径，避免 secure_path 找不到项目内 venv
VENV_PY_ABS="$(pwd)/.venv/bin/python"

if [ -f "pyproject.toml" ]; then
  echo "安装依赖 (uv sync)..."
  uv sync
else
  echo "未找到 pyproject.toml，请确认已执行 just pack 且 build 目录完整。"
  exit 1
fi

if [ -z "${OPENAI_API_KEY}" ] && [ -f ".env" ]; then
  _val=$(grep -E '^\s*OPENAI_API_KEY\s*=' .env 2>/dev/null | head -1 | sed 's/^[^=]*=//' | sed "s/^[\"']//;s/[\"']$//")
  [ -n "${_val}" ] && export OPENAI_API_KEY="${_val}"
  unset _val
fi

# ---------- 前端构建 ----------
if [ -f "claw-fe/package.json" ]; then FRONTEND_DPATH="claw-fe"; else FRONTEND_DPATH="../claw-fe"; fi
if [ "$BACKEND_ONLY" -eq 1 ]; then
  if [ ! -d "$FRONTEND_DPATH/dist" ]; then
    echo "提示: --backend 已跳过前端构建；${FRONTEND_DPATH}/dist 不存在，静态资源可能不可用。"
  fi
elif [ ! -d "$FRONTEND_DPATH/dist" ] && [ -f "$FRONTEND_DPATH/package.json" ]; then
  echo "前端尚未构建，开始 pnpm install && pnpm build..."
  if ! command -v pnpm >/dev/null 2>&1; then
    if command -v corepack >/dev/null 2>&1; then
      corepack enable && corepack prepare pnpm@10.22.0 --activate
    elif command -v npm >/dev/null 2>&1; then
      npm i -g pnpm
    else
      echo "警告: 未找到 pnpm，跳过前端构建。请手动执行: cd claw-fe && pnpm install && pnpm build"
    fi
  fi
  if command -v pnpm >/dev/null 2>&1; then
    (cd "$FRONTEND_DPATH" && pnpm install --frozen-lockfile 2>/dev/null || pnpm install && pnpm build)
  fi
fi

# ---------- 启动 ----------
echo "启动 main.py..."
# Linux 非 root：默认 sudo -E 启动，便于绑定 80 等特权端口；设置 ANOTHERCLAW_NO_SUDO=1 可关闭
_use_sudo=0
if [ "$(uname -s)" = "Linux" ] && [ "$(id -u)" -ne 0 ] && [ -z "${ANOTHERCLAW_NO_SUDO:-}" ]; then
  _use_sudo=1
fi
if [ "$DAEMON" -eq 1 ]; then
  if [ "$_use_sudo" -eq 1 ]; then
    nohup sudo -E "$VENV_PY_ABS" main.py >> anotherclaw.log 2>&1 &
  else
    nohup "$VENV_PY_ABS" main.py >> anotherclaw.log 2>&1 &
  fi
  echo "$!" >"$ROOT/anotherclaw-daemon.pid"
  echo "已后台启动，PID: $!"
  echo "日志: $(pwd)/anotherclaw.log"
  exit 0
fi
if [ "$_use_sudo" -eq 1 ]; then
  exec sudo -E "$VENV_PY_ABS" main.py
else
  exec "$VENV_PY_ABS" main.py
fi
