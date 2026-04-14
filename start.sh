#!/usr/bin/env zsh
# ─────────────────────────────────────────────────────────────────────────────
# SystemAnalyzer — Launcher
# Usage:  ./start.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PORT=5000
APP_URL="http://localhost:${APP_PORT}"
PYTHON="python"

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

banner() {
  echo ""
  echo "${CYAN}${BOLD}╔══════════════════════════════════════════════════════╗${RESET}"
  echo "${CYAN}${BOLD}║          ■  S Y S T E M   A N A L Y Z E R  ■        ║${RESET}"
  echo "${CYAN}${BOLD}║        Fingerprint & CVE Intelligence Platform       ║${RESET}"
  echo "${CYAN}${BOLD}╚══════════════════════════════════════════════════════╝${RESET}"
  echo ""
}

step()  { echo "${BLUE}[•]${RESET} $1"; }
ok()    { echo "${GREEN}[✓]${RESET} $1"; }
warn()  { echo "${YELLOW}[!]${RESET} $1"; }
error() { echo "${RED}[✗]${RESET} $1"; }

# ── Check port ────────────────────────────────────────────────────────────────
port_busy() {
  lsof -ti ":${APP_PORT}" >/dev/null 2>&1
}

kill_port() {
  local pids
  pids=$(lsof -ti ":${APP_PORT}" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    warn "Port ${APP_PORT} in use (PID ${pids}) — killing…"
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 1
    ok "Port ${APP_PORT} freed"
  fi
}

# ── Docker Desktop ────────────────────────────────────────────────────────────
ensure_docker() {
  if ! /Applications/Docker.app/Contents/Resources/bin/docker info >/dev/null 2>&1; then
    warn "Docker Desktop not running — starting it…"
    open /Applications/Docker.app
    local i=0
    while ! /Applications/Docker.app/Contents/Resources/bin/docker info >/dev/null 2>&1; do
      sleep 2
      i=$((i+1))
      if [[ $i -ge 30 ]]; then
        warn "Docker took too long — lab container controls may be unavailable"
        return
      fi
    done
    ok "Docker Desktop ready"
  else
    ok "Docker Desktop is running"
  fi
}

# ── Python deps ───────────────────────────────────────────────────────────────
check_deps() {
  step "Checking Python dependencies…"
  cd "$SCRIPT_DIR"

  local missing=0
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    pkg="${line%%[>=<!]*}"
    if ! $PYTHON -c "import ${pkg//-/_}" >/dev/null 2>&1 && \
       ! $PYTHON -c "import ${pkg}"       >/dev/null 2>&1; then
      warn "Missing: $pkg — installing…"
      $PYTHON -m pip install "$line" -q
      missing=1
    fi
  done < requirements.txt

  # Lab extras
  for pkg in docker python-dateutil; do
    mod="${pkg//-/_}"
    if ! $PYTHON -c "import $mod" >/dev/null 2>&1; then
      warn "Missing: $pkg — installing…"
      $PYTHON -m pip install "$pkg" -q
    fi
  done

  [[ $missing -eq 0 ]] && ok "All dependencies present" || ok "Dependencies installed"
}

# ── Open browser ──────────────────────────────────────────────────────────────
open_browser() {
  local url="$1"
  step "Opening ${url} in browser…"
  # Wait until Flask is actually accepting connections
  local i=0
  while ! curl -s --max-time 1 "$url" >/dev/null 2>&1; do
    sleep 0.5
    i=$((i+1))
    [[ $i -ge 20 ]] && break
  done
  open "$url"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  banner

  step "Working directory: ${SCRIPT_DIR}"
  cd "$SCRIPT_DIR"

  # 1. Free the port if busy
  kill_port

  # 2. Ensure Docker is running (for lab)
  ensure_docker

  # 3. Check Python deps
  check_deps

  echo ""
  echo "${BOLD}Starting SystemAnalyzer on ${APP_URL}${RESET}"
  echo "${CYAN}──────────────────────────────────────────────────────${RESET}"
  echo "  Dashboard  →  ${APP_URL}/dashboard"
  echo "  Lab        →  ${APP_URL}/lab"
  echo "  Generate   →  ${APP_URL}/generate"
  echo "${CYAN}──────────────────────────────────────────────────────${RESET}"
  echo "  Press ${BOLD}Ctrl+C${RESET} to stop"
  echo ""

  # 4. Open browser in background once the server is up
  open_browser "${APP_URL}/dashboard" &

  # 5. Launch Flask
  exec $PYTHON app.py
}

main "$@"
