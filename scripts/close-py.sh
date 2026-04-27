#!/bin/bash
# 关闭 start-d / start-py.sh --daemon 启动的后台 main.py
# 从项目根执行：just close

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

if [ ! -f "$PIDFILE" ]; then
  echo "未找到 $PIDFILE，可能没有通过 just start-d 启动后台进程。"
  exit 0
fi

PID="$(tr -d ' \n\r\t' <"$PIDFILE" || true)"
if [ -z "$PID" ] || ! [[ "$PID" =~ ^[0-9]+$ ]]; then
  echo "PID 文件内容无效，已删除: $PIDFILE"
  rm -f "$PIDFILE"
  exit 1
fi

if ! kill -0 "$PID" 2>/dev/null; then
  echo "进程 $PID 已不存在，清理 PID 文件。"
  rm -f "$PIDFILE"
  exit 0
fi

echo "正在终止后台进程 PID=$PID ..."
kill "$PID" 2>/dev/null || true
# 等待最多约 5s
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if ! kill -0 "$PID" 2>/dev/null; then
    break
  fi
  sleep 0.5
done
if kill -0 "$PID" 2>/dev/null; then
  echo "SIGTERM 未结束进程，发送 SIGKILL..."
  kill -9 "$PID" 2>/dev/null || true
fi
rm -f "$PIDFILE"
echo "已关闭。"
