#!/bin/bash
# 查看 start-d 后台进程状态（anotherclaw-daemon.pid）
# 从项目根执行：just status
# Show status of backend started via start-d / anotherclaw-daemon.pid

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -d "$PWD/claw-be-py" ]; then
  ROOT="$PWD"
elif [ -f "$PWD/main.py" ] && [ -f "$PWD/pyproject.toml" ]; then
  ROOT="$PWD"
else
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

PIDFILE="$ROOT/anotherclaw-daemon.pid"

echo "AnotherClaw 后台进程（start-d / anotherclaw-daemon.pid）"
echo "PID 文件: $PIDFILE"
echo ""

if [ ! -f "$PIDFILE" ]; then
  echo "状态: 未启动（无 PID 文件）"
  echo "提示: 使用 just start-d 在后台启动后端。"
  exit 0
fi

PID="$(tr -d ' \n\r\t' <"$PIDFILE" || true)"
if [ -z "$PID" ] || ! [[ "$PID" =~ ^[0-9]+$ ]]; then
  echo "状态: PID 文件内容无效"
  exit 1
fi

if ! kill -0 "$PID" 2>/dev/null; then
  echo "状态: 已停止（PID $PID 不存在，可手动删除陈旧文件: rm \"$PIDFILE\"）"
  exit 0
fi

echo "状态: 运行中"
echo "PID: $PID"
ps -p "$PID" 2>/dev/null || true
