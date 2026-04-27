# 打包产物目录用：仅含 build 内可用命令（pack 时复制为 build/justfile） (Minimal recipes for packaged build/; copied to build/justfile by pack)
set shell := ["bash", "-cu"]

# 列出可用 recipe (List available recipes)
default:
    @just --list

# 固定版本号 (Print pinned version)
version:
    @echo "1.0.0"

# 启动后端（前台）(Start backend, foreground)
start:
    bash scripts/start-py.sh --py

# 启动后端（后台）(Start backend, daemon)
start-d:
    bash scripts/start-py.sh --py --daemon

# close 别名 (Alias for close-py)
close: close-py

# 关闭 start-d 的后台进程 (Stop backend daemon from start-d)
close-py:
    bash scripts/close-py.sh

# 查看 start-d 后台进程状态 (Show backend daemon PID / process status)
status:
    bash scripts/status-py.sh
