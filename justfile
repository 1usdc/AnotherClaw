# 打包产物目录用：仅含 build 内可用命令（pack 时复制为 build/justfile） (Minimal recipes for packaged build/; copied to build/justfile by pack)
set shell := ["bash", "-cu"]

# 列出可用功能 (List available recipes)
default:
    @just --list

# 版本号：与 VERSION 文件一致 (Print version from VERSION file)
version:
    @cat VERSION 2>/dev/null || echo "1.0.0"

# 启动后端（前台）(Start backend, foreground)
start:
    bash scripts/start-py.sh --py

# 启动后端（后台；PID 仍存活则跳过）(Start backend, daemon; skip if PID alive)
start-d:
    bash scripts/start-py.sh --py --daemon

# 关闭 start-d 的后台进程 (Stop backend daemon from start-d)
close:
    bash scripts/close-py.sh

# 查看 start-d 后台进程状态 (Show backend daemon PID / process status)
status:
    bash scripts/status-py.sh

# 配置 Linux systemd 开机自启动 (Install Linux systemd autostart)
auto-start:
    bash scripts/autostart-py.sh start

# 取消 Linux systemd 开机自启动 (Remove Linux systemd autostart)
auto-close:
    bash scripts/autostart-py.sh close

# 查看 Linux systemd 开机自启动状态 (Show Linux systemd autostart status)
auto-status:
    bash scripts/autostart-py.sh status

# 在 Linux 上安装 nginx（apt/dnf/yum/apk）(Install nginx on Linux)
nginx-install:
    bash scripts/nginx.sh install

# 配置 nginx：80 反代到本机 8765（可用 NGINX_UPSTREAM_PORT 覆盖）(nginx reverse proxy 80 -> 8765)
nginx-set:
    bash scripts/nginx.sh set

# 重启 nginx (Restart nginx)
nginx-restart:
    bash scripts/nginx.sh restart