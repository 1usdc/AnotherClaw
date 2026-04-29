#!/usr/bin/env bash
# 一键推送项目根仓库到 openclaw 远程

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT"
OPENCLAW_REPO="${OPENCLAW_REPO_URL:-https://github.com/1bnb/openclaw.git}"

git add .
if ! git diff --cached --quiet; then
  MSG="${COMMIT_MSG:-chore: sync $(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  git commit -m "$MSG"
else
  echo "工作区无变更，跳过 commit"
fi

if ! git remote get-url openclaw &>/dev/null; then
  git remote add openclaw "$OPENCLAW_REPO"
else
  git remote set-url openclaw "$OPENCLAW_REPO"
fi

echo "推送到 $OPENCLAW_REPO ..."
git push -u openclaw main --force 2>/dev/null || git push -u openclaw HEAD:main --force
