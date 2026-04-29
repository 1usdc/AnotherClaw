#!/usr/bin/env bash
# One-click install dependencies and bootstrap for this project (Linux, e.g. Ubuntu/Debian, or containers).
# Usage: see QUICKSTART_USAGE after set -e. Project is always cloned/used at ~/AnotherClaw ($HOME/AnotherClaw).

set -e
REPO_URL="${ANOTHERCLAW_REPO_URL:-https://github.com/1usdc/AnotherClaw.git}"
DEPS_ONLY=0
readonly QUICKSTART_USAGE="Usage: bash scripts/quickstart.sh [--deps]"

for arg in "$@"; do
  case "$arg" in
    --deps)
      DEPS_ONLY=1
      ;;
    *)
      echo "Unknown argument: $arg"
      echo "$QUICKSTART_USAGE"
      exit 1
      ;;
  esac
done

INSTALL_DIR="$HOME/AnotherClaw"

# Probes country ISO via three public HTTP APIs in parallel; first non-empty wins, others are killed.
detect_country_code() {
  local url code urls i tmpdir pids pid f deadline alive

  if ! command -v curl &>/dev/null && ! command -v wget &>/dev/null; then
    echo ""
    return 0
  fi

  urls=(
    "https://ipinfo.io/country"
    "https://ifconfig.co/country-iso"
    "https://ipapi.co/country/"
  )

  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/anotherclaw-country.XXXXXX")" || {
    echo ""
    return 0
  }

  pids=()
  i=0
  for url in "${urls[@]}"; do
    (
      local c=""
      if command -v curl &>/dev/null; then
        c="$(curl -fsSL --max-time 4 "$url" 2>/dev/null | tr -d '\r\n[:space:]' || true)"
      else
        c="$(wget -qO- --timeout=4 "$url" 2>/dev/null | tr -d '\r\n[:space:]' || true)"
      fi
      if [ -n "$c" ]; then
        printf '%s' "$c" >"$tmpdir/ok.$i"
      fi
    ) &
    pids+=("$!")
    i=$((i + 1))
  done

  deadline=$((SECONDS + 13))
  while [ "$SECONDS" -lt "$deadline" ]; do
    for f in "$tmpdir/ok.0" "$tmpdir/ok.1" "$tmpdir/ok.2"; do
      [ -f "$f" ] || continue
      code="$(tr -d '\r\n[:space:]' <"$f" 2>/dev/null || true)"
      if [ -n "$code" ]; then
        for pid in "${pids[@]}"; do
          kill "$pid" 2>/dev/null || true
        done
        for pid in "${pids[@]}"; do
          wait "$pid" 2>/dev/null || true
        done
        rm -rf "$tmpdir"
        echo "$code"
        return 0
      fi
    done

    alive=0
    for pid in "${pids[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then
        alive=1
        break
      fi
    done
    if [ "$alive" -eq 0 ]; then
      break
    fi
    sleep 0.1
  done

  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  done
  rm -rf "$tmpdir"
  echo ""
}

APT_MIRROR_ENABLED=0
APT_MIRROR_DIR=""

cleanup_temp_mirror() {
  if [ -n "${APT_MIRROR_DIR:-}" ] && [ -d "$APT_MIRROR_DIR" ]; then
    rm -rf "$APT_MIRROR_DIR" || true
  fi
}

# Rewrite upstream Debian/Ubuntu apt hosts to Aliyun mirror (single sed program).
rewrite_apt_sources_to_aliyun() {
  sed 's|https\?://\(archive.ubuntu.com\|security.ubuntu.com\|deb.debian.org\|ftp.debian.org\)|https://mirrors.aliyun.com|g' "$1"
}

# Run apt as root; when not root, use sudo so `curl … | bash` keeps $HOME as the normal user.
run_apt() {
  if [ "$(id -u)" -eq 0 ]; then
    apt "$@"
  elif command -v sudo &>/dev/null; then
    sudo apt "$@"
  else
    echo "  [apt] need root for package install; install sudo or run as root." >&2
    return 1
  fi
}

# Synchronous apt: optional temporary CN mirror from setup_cn_mirror_temporarily (no lock/subshell).
sync_apt() {
  if [ "$APT_MIRROR_ENABLED" = "1" ]; then
    run_apt \
      -o "Dir::Etc::sourcelist=$APT_MIRROR_DIR/sources.list" \
      -o "Dir::Etc::sourceparts=$APT_MIRROR_DIR/sources.list.d" \
      "$@"
  else
    run_apt "$@"
  fi
}

setup_cn_mirror_temporarily() {
  local country
  country="$(detect_country_code | tr '[:lower:]' '[:upper:]')"
  if [ "$country" != "CN" ]; then
    echo "=== IP region: ${country:-unknown}, using default mirrors ==="
    return 0
  fi
  echo "=== IP region: CN, switching to temporary Aliyun mirrors ==="

  # Temporary npm/pnpm mirrors: only for this script process, no writes to ~/.npmrc.
  export NPM_CONFIG_REGISTRY="https://registry.npmmirror.com"
  export PNPM_CONFIG_REGISTRY="$NPM_CONFIG_REGISTRY"

  if command -v apt &>/dev/null; then
    APT_MIRROR_DIR="$(mktemp -d /tmp/anotherclaw-apt.XXXXXX)"
    mkdir -p "$APT_MIRROR_DIR/sources.list.d"

    if [ -f /etc/apt/sources.list ]; then
      rewrite_apt_sources_to_aliyun /etc/apt/sources.list >"$APT_MIRROR_DIR/sources.list"
    else
      : >"$APT_MIRROR_DIR/sources.list"
    fi

    if [ -d /etc/apt/sources.list.d ]; then
      for f in /etc/apt/sources.list.d/*.list; do
        [ -f "$f" ] || continue
        rewrite_apt_sources_to_aliyun "$f" >"$APT_MIRROR_DIR/sources.list.d/$(basename "$f")"
      done
    fi

    APT_MIRROR_ENABLED=1
    trap cleanup_temp_mirror EXIT
    echo "=== apt will use temporary Aliyun mirrors only in this script (no host config changes) ==="
  fi
}

setup_cn_mirror_temporarily

if [ "$DEPS_ONLY" -eq 0 ]; then
  if [ -d "$INSTALL_DIR" ] && [ ! -d "$INSTALL_DIR/.git" ]; then
    echo "  Directory exists and is not a git repository; remove or rename: $INSTALL_DIR"
    exit 1
  fi
fi

if [ "$DEPS_ONLY" -eq 1 ] && [ ! -d "$INSTALL_DIR" ]; then
  echo "未找到项目目录: $INSTALL_DIR"
  echo "当前为 --deps 模式；请先将仓库放到 ~/AnotherClaw 后再运行。"
  exit 1
fi

if command -v apt &>/dev/null; then
  sync_apt update -qq
fi

echo "=== Sync: git | Async: clone ∥ (node→pnpm→just→podman) ∥ uv ==="
ASYNC_PIDS=()
ASYNC_NAMES=()

run_async() {
  local name="$1"
  shift
  (
    "$@"
  ) &
  ASYNC_PIDS+=("$!")
  ASYNC_NAMES+=("$name")
}

wait_async() {
  local idx failed
  failed=0
  for idx in "${!ASYNC_PIDS[@]}"; do
    if wait "${ASYNC_PIDS[$idx]}"; then
      echo "  [OK] ${ASYNC_NAMES[$idx]}"
    else
      echo "  [FAIL] ${ASYNC_NAMES[$idx]}"
      failed=1
    fi
  done
  if [ "$failed" -ne 0 ]; then
    echo "依赖安装失败，请查看上方日志。"
    exit 1
  fi
}

# Install Node only (one package-manager invocation). Does not install just/podman.
install_node_only_via_pm() {
  if command -v node &>/dev/null; then
    echo "  [node] already installed ($(node -v))"
    return 0
  fi
  if command -v apt &>/dev/null; then
    echo "  [apt] installing: nodejs npm"
    sync_apt install -y nodejs npm
    return 0
  fi
  if command -v yum &>/dev/null; then
    echo "  [yum] installing: nodejs npm"
    yum install -y nodejs npm
    return 0
  fi
  if command -v brew &>/dev/null; then
    echo "  [brew] installing: node"
    brew install node
    return 0
  fi
  echo "  [node] Unrecognized package manager. Install Node.js manually: https://nodejs.org/"
  return 1
}

# Install just + podman in one package-manager invocation when possible (after pnpm).
install_just_podman_batched() {
  local pkgs=()
  if command -v apt &>/dev/null; then
    if ! command -v just &>/dev/null; then
      pkgs+=(just)
    fi
    if ! command -v podman &>/dev/null; then
      pkgs+=(podman)
    fi
    if [ "${#pkgs[@]}" -eq 0 ]; then
      echo "  [just/podman] already installed"
      return 0
    fi
    echo "  [apt] installing: ${pkgs[*]}"
    sync_apt install -y "${pkgs[@]}"
    return 0
  fi

  if command -v yum &>/dev/null; then
    if ! command -v just &>/dev/null; then
      pkgs+=(just)
    fi
    if ! command -v podman &>/dev/null; then
      pkgs+=(podman)
    fi
    if [ "${#pkgs[@]}" -eq 0 ]; then
      echo "  [just/podman] already installed"
      return 0
    fi
    echo "  [yum] installing: ${pkgs[*]}"
    yum install -y "${pkgs[@]}"
    return 0
  fi

  if command -v brew &>/dev/null; then
    if ! command -v just &>/dev/null; then
      pkgs+=(just)
    fi
    if ! command -v podman &>/dev/null; then
      pkgs+=(podman)
    fi
    if [ "${#pkgs[@]}" -eq 0 ]; then
      echo "  [just/podman] already installed"
      return 0
    fi
    echo "  [brew] installing: ${pkgs[*]}"
    brew install "${pkgs[@]}"
    return 0
  fi

  echo "  [just/podman] Unrecognized package manager. Install just and podman manually."
  return 1
}

install_git_if_needed() {
  if command -v git &>/dev/null; then
    echo "  [git] already installed"
    return 0
  fi
  if ! command -v apt &>/dev/null; then
    echo "  [git] apt not found; install git manually"
    return 1
  fi
  echo "  [git] installing ..."
  sync_apt install -y git
}

clone_repo_if_needed() {
  if [ "$DEPS_ONLY" -eq 1 ]; then
    echo "  [clone] skipped (--deps)"
    return 0
  fi
  if [ -d "$INSTALL_DIR/.git" ]; then
    echo "  [clone] repository already at $INSTALL_DIR"
    return 0
  fi
  if ! command -v git &>/dev/null; then
    echo "  [clone] git not found"
    return 1
  fi
  if [ -d "$INSTALL_DIR" ]; then
    echo "  [clone] directory exists and is not a git repository"
    return 1
  fi
  echo "  [clone] cloning to $INSTALL_DIR ..."
  git clone "$REPO_URL" "$INSTALL_DIR"
}

# 将 ~/.local/bin 写入 profile，避免 quickstart 子 shell 里的 export 在 just/SSH 中丢失
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
  echo "  [uv] 已将 ~/.local/bin 追加到 $target（重新登录或 source 后全局生效）"
}

install_uv_if_needed() {
  if command -v uv &>/dev/null; then
    echo "  [uv] already installed"
    return 0
  fi
  export PATH="$HOME/.local/bin${PATH:+:$PATH}"
  if command -v uv &>/dev/null; then
    echo "  [uv] already installed (~/.local/bin)"
    persist_user_local_bin_path
    return 0
  fi
  echo "  [uv] installing ..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin${PATH:+:$PATH}"
  if command -v uv &>/dev/null; then
    persist_user_local_bin_path
  fi
  command -v uv &>/dev/null
}

install_pnpm_if_needed() {
  if command -v pnpm &>/dev/null; then
    echo "  [pnpm] already installed ($(pnpm --version))"
    return 0
  fi
  if ! command -v node &>/dev/null; then
    echo "  [pnpm] node not found (node install may have failed)"
    return 1
  fi
  if ! command -v npm &>/dev/null && ! command -v corepack &>/dev/null; then
    echo "  [pnpm] npm/corepack not found"
    return 1
  fi
  echo "  [pnpm] installing ..."
  if command -v corepack &>/dev/null; then
    corepack enable
    corepack prepare pnpm@latest --activate
  else
    npm i -g pnpm
  fi
  command -v pnpm &>/dev/null
}

install_chain_node_pnpm_just_podman() {
  install_node_only_via_pm
  install_pnpm_if_needed
  install_just_podman_batched
}

install_git_if_needed

run_async "clone" clone_repo_if_needed
run_async "node→pnpm→just→podman" install_chain_node_pnpm_just_podman
run_async "uv" install_uv_if_needed

wait_async

if [ ! -d "$INSTALL_DIR" ]; then
  echo "未找到项目目录: $INSTALL_DIR（克隆可能失败）"
  exit 1
fi

cd "$INSTALL_DIR"

if [ "$DEPS_ONLY" -eq 1 ]; then
  echo "Dependencies installation completed (--deps)."
else
  echo "Installation completed. To start:"
  echo "1. cd $INSTALL_DIR"
  echo "2. just start-d"
fi
