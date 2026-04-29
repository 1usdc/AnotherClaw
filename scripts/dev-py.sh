#!/bin/bash
# 开发模式：先打包前端（claw-fe/dist），再仅启动后端 main.py（后端会挂载 claw-fe/dist 提供页面）
# 从项目根执行：just dev（脚本位于 scripts/dev-py.sh）

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND="$ROOT/claw-be-py"

# 必须在项目根（含 scripts/pack-py.sh）
if [ ! -f "$ROOT/scripts/pack-py.sh" ]; then
  echo "请在项目根目录执行 just dev。"
  exit 1
fi

# 确保 backend 存在
if [ ! -d "$BACKEND" ]; then
  echo "错误: backend 目录不存在: $BACKEND"
  echo "请确认从正确的项目根执行（项目根应包含 claw-be-py/ 与 scripts/）"
  exit 1
fi

cd "$BACKEND"

# ---------- 后端：uv/venv/依赖 ----------
# 已有可用 .venv 时直接走启动路径（跳过 uv 安装与 uv sync）；首次或损坏则引导创建并 sync
HAVE_VENV=0
if [ -x ".venv/bin/python" ]; then
  HAVE_VENV=1
fi

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    return 0
  fi
  echo "未检测到 uv，开始自动安装..."
  if ! command -v curl >/dev/null 2>&1; then
    echo "未找到 curl，请先安装 curl。"
    exit 1
  fi
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin${PATH:+:$PATH}"
}

if [ "$HAVE_VENV" -eq 0 ]; then
  ensure_uv
  if [ -d ".venv" ]; then
    echo "检测到 .venv 存在但不可用，使用 --clear 非交互重建..."
    uv venv --clear .venv
  else
    echo "创建虚拟环境 .venv..."
    uv venv .venv
  fi
fi

if [ -f "pyproject.toml" ]; then
  if [ "$HAVE_VENV" -eq 0 ] || [ "${FORCE_UV_SYNC:-}" = "1" ]; then
    ensure_uv
    echo "安装依赖 (uv sync)..."
    uv sync
  else
    echo "检测到已有虚拟环境，跳过 uv sync（强制同步: FORCE_UV_SYNC=1 just dev）"
  fi
else
  echo "未找到 pyproject.toml（预期在 $BACKEND），请在项目根目录执行 just dev。"
  exit 1
fi
VENV_PY=".venv/bin/python"

if [ -z "${OPENAI_API_KEY}" ] && [ -f ".env" ]; then
  _val=$(grep -E '^\s*OPENAI_API_KEY\s*=' .env 2>/dev/null | head -1 | sed 's/^[^=]*=//' | sed "s/^[\"']//;s/[\"']$//")
  [ -n "${_val}" ] && export OPENAI_API_KEY="${_val}"
  unset _val
fi

# ---------- 前端：打包到 claw-fe/dist（项目根 $ROOT/claw-fe，包管理：pnpm）----------
if [ -f "$ROOT/claw-fe/package.json" ]; then
  if ! command -v pnpm >/dev/null 2>&1; then
    if command -v corepack >/dev/null 2>&1; then
      corepack enable && corepack prepare pnpm@10.22.0 --activate
    elif command -v npm >/dev/null 2>&1; then
      npm i -g pnpm
    else
      echo "错误: 未找到 pnpm。请安装 Node.js 后执行: corepack enable && corepack prepare pnpm@10.22.0 --activate"
      echo "说明: https://pnpm.io/installation"
      exit 1
    fi
  fi
  if [ ! -d "$ROOT/claw-fe/node_modules" ]; then
    echo "安装前端依赖 (claw-fe/)..."
    (cd "$ROOT/claw-fe" && pnpm install --frozen-lockfile)
  fi
  echo "打包前端 (claw-fe/ -> claw-fe/dist)..."
  (cd "$ROOT/claw-fe" && pnpm run build)
  if [ ! -d "$ROOT/claw-fe/dist" ] || [ ! -f "$ROOT/claw-fe/dist/index.html" ]; then
    echo "前端构建未生成 claw-fe/dist/index.html，请检查上方输出。"
    exit 1
  fi
  echo "前端已构建到 claw-fe/dist/"
fi

# ---------- 仅启动后端（前台）----------
exec "$VENV_PY" main.py
