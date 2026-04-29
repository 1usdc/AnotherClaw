#!/usr/bin/env bash
# 打包脚本：python-minifier 压缩 -> claw-be-py/build/，前端 Vite 构建 -> claw-fe/dist/，并拷贝 claw-fe、justfile、scripts 等。
# 依赖：uv、python-minifier（pyminify）、pnpm。使用：在项目根执行 ./scripts/pack-py.sh 或 just pack

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/claw-be-py"
CLAW_FE_DIR="$ROOT/claw-fe"
OUT="$BACKEND/build"
# 始终使用 claw-be-py 的 .venv
unset VIRTUAL_ENV
export PATH="$BACKEND/.venv/bin:$PATH"

echo "=== 1. python-minifier 压缩 -> $OUT ==="
if [ ! -x "$BACKEND/.venv/bin/python" ]; then
  if [ -d "$BACKEND/.venv" ]; then
    echo "检测到 .venv 存在但不可用，使用 --clear 非交互重建..."
    uv venv --clear "$BACKEND/.venv"
  else
    echo "创建虚拟环境 .venv..."
    uv venv "$BACKEND/.venv"
  fi
fi
if [ -f "$BACKEND/pyproject.toml" ]; then
  (cd "$BACKEND" && uv sync)
fi
if ! "$BACKEND/.venv/bin/python" -c "import python_minifier" 2>/dev/null; then
  echo "正在尝试安装 python-minifier..."
  uv pip install --python "$BACKEND/.venv/bin/python" python-minifier 2>/dev/null || true
fi
PY="$BACKEND/.venv/bin/python"
if ! "$PY" -c "import python_minifier" 2>/dev/null; then
  echo "请先安装 python-minifier: uv pip install --python $PY python-minifier"
  exit 1
fi
# build/ 为单独仓库，由 push-py.sh 推送到另一 GitHub，打包时保留其 .git
if [ -d "$OUT/.git" ]; then
  mv "$OUT/.git" "$BACKEND/.git.build.bak"
fi
rm -rf "$OUT"
mkdir -p "$OUT" "$OUT/agents" "$OUT/tools" "$OUT/routes" "$OUT/utils" "$OUT/skills"
# 先拷贝 .py 到 build，再对 build 目录整体 --in-place 压缩（用 claw-be-py 的 Python 调用，避免 pyminify 脚本 shebang 指向错误）
cp "$BACKEND/main.py" "$OUT/"
cp "$BACKEND/agents/"*.py "$OUT/agents/"
cp "$BACKEND/tools/"*.py "$OUT/tools/"
cp "$BACKEND/routes/"*.py "$OUT/routes/"
cp "$BACKEND/utils/"*.py "$OUT/utils/"
# 保留参数类型注解，避免 FastAPI 将 request 等参数误判为 query 导致 422
"$PY" -m python_minifier "$OUT" --in-place --no-remove-argument-annotations
echo "  python-minifier 完成"

echo "=== 2. 前端 Vite 构建 -> claw-fe/dist/（打包时会拷贝到 $OUT/claw-fe/dist/）==="
if [ -f "$CLAW_FE_DIR/package.json" ]; then
  if ! command -v pnpm &>/dev/null; then
    echo "未检测到 pnpm，开始自动安装..."
    if command -v curl &>/dev/null; then
      curl -fsSL https://get.pnpm.io/install.sh | sh -
      export PNPM_HOME="${PNPM_HOME:-$HOME/.local/share/pnpm}"
      export PATH="$PNPM_HOME:$PATH"
    elif command -v npm &>/dev/null; then
      npm i -g pnpm
    else
      echo "无法安装 pnpm：请先安装 curl 或 npm，或手动安装 pnpm"
      exit 1
    fi
    if ! command -v pnpm &>/dev/null; then
      export PNPM_HOME="${PNPM_HOME:-$HOME/.local/share/pnpm}"
      export PATH="$PNPM_HOME:$PATH"
    fi
    if ! command -v pnpm &>/dev/null; then
      echo "pnpm 安装后仍不可用，请检查 PATH 或手动安装: npm i -g pnpm"
      exit 1
    fi
    echo "  pnpm 已就绪"
  fi
  echo "  cd claw-fe && pnpm install..."
  (cd "$CLAW_FE_DIR" && pnpm install)
  echo "  cd claw-fe && pnpm build..."
  (cd "$CLAW_FE_DIR" && pnpm build)
  if [ -d "$CLAW_FE_DIR/dist" ] && [ -f "$CLAW_FE_DIR/dist/index.html" ]; then
    echo "  前端已构建到 claw-fe/dist/"
  else
    echo "  未生成 claw-fe/dist/，请检查上方构建输出"
    exit 1
  fi
else
  echo "  未找到 claw-fe/package.json（预期在项目根 $CLAW_FE_DIR），跳过前端构建"
fi

echo "=== 3. 拷贝 claw-fe/dist、空 skills/、agents/prompts/、pyproject.toml、uv.lock、.env.example、scripts/、justfile.build→justfile 到 $OUT ==="
if [ -f "$CLAW_FE_DIR/package.json" ] && [ ! -f "$CLAW_FE_DIR/dist/index.html" ]; then
  echo "claw-fe/dist 不存在，先执行前端打包..."
  if ! command -v pnpm &>/dev/null; then
    if command -v corepack &>/dev/null; then
      corepack enable && corepack prepare pnpm@10.22.0 --activate
    elif command -v npm &>/dev/null; then
      npm i -g pnpm
    else
      echo "  未找到 pnpm，无法自动构建前端（请安装 Node.js 与 pnpm）"
      exit 1
    fi
  fi
  (cd "$CLAW_FE_DIR" && pnpm install && pnpm build)
  [ ! -f "$CLAW_FE_DIR/dist/index.html" ] && echo "  前端构建未生成 claw-fe/dist/index.html" && exit 1
fi
if [ -d "$CLAW_FE_DIR/dist" ]; then
  mkdir -p "$OUT/claw-fe"
  cp -r "$CLAW_FE_DIR/dist" "$OUT/claw-fe/"
  echo "  已复制 claw-fe/dist/"
fi
echo "  已创建空目录 skills/"
if [ -d "$BACKEND/agents/prompts" ]; then
  mkdir -p "$OUT/agents"
  (cd "$BACKEND/agents" && tar --exclude='.git' -cf - prompts) | (cd "$OUT/agents" && tar -xf -)
  echo "  已复制 agents/prompts/"
fi
for f in pyproject.toml uv.lock .env.example; do
  if [ -f "$BACKEND/$f" ]; then
    cp "$BACKEND/$f" "$OUT/"
    echo "  已复制 $f"
  fi
done
if [ -f "$ROOT/justfile.build" ]; then
  cp "$ROOT/justfile.build" "$OUT/justfile"
  echo "  已复制 justfile.build -> build/justfile（仅含 build 可用命令）"
elif [ -f "$ROOT/justfile" ]; then
  cp "$ROOT/justfile" "$OUT/justfile"
  echo "  已复制 justfile -> build/justfile"
fi
if [ -d "$ROOT/scripts" ]; then
  rm -rf "$OUT/scripts"
  cp -a "$ROOT/scripts" "$OUT/scripts"
  # 不把本地 secrets 打进 build（若存在）
  rm -f "$OUT/scripts/.env"
  find "$OUT/scripts" -type f -name '*.sh' -exec chmod +x {} \;
  echo "  已复制 scripts/ -> build/scripts/（已移除 build/scripts/.env 若存在）"
fi
# 恢复 build 的 .git，便于 just push-py 推送到另一 GitHub
if [ -d "$BACKEND/.git.build.bak" ]; then
  mv "$BACKEND/.git.build.bak" "$OUT/.git"
  echo "  已恢复 build/.git（单独仓库）"
fi
echo ""
echo "完成。生产运行：进入 claw-be-py/build 目录后启动："
echo "  cd claw-be-py/build && just start"
