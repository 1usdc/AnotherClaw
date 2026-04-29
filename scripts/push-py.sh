#!/usr/bin/env bash
# 在项目根目录执行，对 build/ 目录做 git init 并推送到 GitHub。
# 用法：在项目根目录执行 ./scripts/push-py.sh 或 just push-py
#
# 版本号：
#   交互终端：提示「请输入版本号」，直接回车则使用自动生成版本号。
#   非交互（CI）：默认使用自动版本号。
#   环境变量 PUSH_VERSION=x.y.z 可跳过提示，直接使用该完整版本号（并写入根目录 VERSION）。

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$ROOT/claw-be-py/build"

if [ ! -d "$BUILD_DIR" ]; then
  echo "build 目录不存在，请先执行 just pack"
  exit 1
fi
cd "$BUILD_DIR"

# 优先使用环境变量 GITHUB_TOKEN；若未设置则从 .env 读取（先 root/.env，再 scripts/.env）
if [ -z "${GITHUB_TOKEN:-}" ]; then
  for env_file in "$ROOT/.env" "$SCRIPT_DIR/.env"; do
    [ -f "$env_file" ] || continue
    token_line="$(sed -n 's/^[[:space:]]*GITHUB_TOKEN[[:space:]]*=[[:space:]]*//p' "$env_file" | head -n1)"
    token_line="$(echo "$token_line" | sed "s/[[:space:]]*$//" | sed "s/^['\"]//;s/['\"]$//")"
    if [ -n "$token_line" ]; then
      GITHUB_TOKEN="$token_line"
      export GITHUB_TOKEN
      break
    fi
  done
fi

: "${GITHUB_TOKEN:?请先设置 GITHUB_TOKEN（环境变量，或写入 .env 的 GITHUB_TOKEN=...）}"
REPO_URL="https://x-access-token:${GITHUB_TOKEN}@github.com/1usdc/AnotherClaw.git"

if [ ! -d ".git" ]; then
  git init
fi

# 不把 .env、data 提交上去：加入 .gitignore 并从暂存区移除（若曾被跟踪）
if [ -f ".gitignore" ]; then
  grep -qE '^\.env$' .gitignore 2>/dev/null || echo ".env" >> .gitignore
  grep -qE '^data$' .gitignore 2>/dev/null || echo "data" >> .gitignore
else
  echo -e ".env\ndata" >> .gitignore
fi
git rm --cached .env 2>/dev/null || true
git rm -r --cached data 2>/dev/null || true

# 版本号：根目录 VERSION 为基础版本；与 git describe 组合为「自动完整版本」
if [ -f "$ROOT/VERSION" ]; then
  BASE_VERSION="$(tr -d '\r\n' < "$ROOT/VERSION" | head -n1)"
  [ -n "$BASE_VERSION" ] || BASE_VERSION="1.0.0"
else
  BASE_VERSION="1.0.0"
fi
if GIT_DESC="$(git -C "$ROOT" describe --tags --always --dirty 2>/dev/null)"; then
  AUTO_FULL_VERSION="${BASE_VERSION}+${GIT_DESC}"
else
  AUTO_FULL_VERSION="${BASE_VERSION}+$(date '+%Y%m%d%H%M%S')"
fi

if [ -n "${PUSH_VERSION:-}" ]; then
  FULL_VERSION="$(echo "$PUSH_VERSION" | tr -d '\r\n')"
  printf '%s\n' "$FULL_VERSION" > "$ROOT/VERSION"
  echo "使用环境变量 PUSH_VERSION: $FULL_VERSION（已写入根目录 VERSION）"
elif [ -t 0 ] && [ -t 1 ]; then
  echo ""
  echo "—— 版本号 ——"
  echo "  当前 VERSION 文件基础版本: $BASE_VERSION"
  echo "  自动生成的完整版本号:     $AUTO_FULL_VERSION"
  echo ""
  read -r -p "请输入版本号（直接回车使用自动版本）: " manual_ver
  manual_ver="$(echo "$manual_ver" | tr -d '\r\n')"
  if [ -n "$manual_ver" ]; then
    FULL_VERSION="$manual_ver"
    printf '%s\n' "$FULL_VERSION" > "$ROOT/VERSION"
    echo "已使用手动版本: $FULL_VERSION（已写入根目录 VERSION）"
  else
    FULL_VERSION="$AUTO_FULL_VERSION"
    echo "未输入版本号，使用自动版本: $FULL_VERSION"
  fi
  echo ""
else
  FULL_VERSION="$AUTO_FULL_VERSION"
  echo "非交互环境，使用自动版本号: $FULL_VERSION"
fi

printf '%s\n' "$FULL_VERSION" > "$BUILD_DIR/VERSION"

git add .
git status --short

MSG="v${FULL_VERSION} | $(date '+%Y-%m-%d %H:%M:%S')"
if ! git diff --staged --quiet 2>/dev/null; then
  git commit -m "$MSG"
else
  echo "无变更，跳过提交；继续推送已有提交。"
fi

git branch -M main

if git remote get-url origin &>/dev/null; then
  git remote set-url origin "$REPO_URL"
else
  git remote add origin "$REPO_URL"
fi

git push -u origin main --force