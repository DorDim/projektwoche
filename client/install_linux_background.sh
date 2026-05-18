#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash ./client/install_linux_background.sh \
    --server-url "http://SERVER:8000" \
    --api-key "TOKEN_ODER_API_KEY" \
    [--interval-seconds 60] \
    [--service-name hardware-monitor-client-agent]
EOF
}

SERVER_URL=""
API_KEY=""
INTERVAL_SECONDS="60"
SERVICE_NAME="hardware-monitor-client-agent"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server-url)
      SERVER_URL="${2:-}"
      shift 2
      ;;
    --api-key)
      API_KEY="${2:-}"
      shift 2
      ;;
    --interval-seconds)
      INTERVAL_SECONDS="${2:-60}"
      shift 2
      ;;
    --service-name)
      SERVICE_NAME="${2:-hardware-monitor-client-agent}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unbekannter Parameter: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$SERVER_URL" || -z "$API_KEY" ]]; then
  echo "--server-url und --api-key sind erforderlich." >&2
  usage
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 nicht gefunden. Bitte Python 3 installieren." >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"
VENV_PYTHON="$VENV_DIR/bin/python3"
REQUIREMENTS_FILE="$REPO_ROOT/requirements.txt"
RUNNER_SCRIPT="$REPO_ROOT/client/linux_agent_runner.sh"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Erstelle virtuelle Umgebung..."
  python3 -m venv "$VENV_DIR"
fi

echo "Installiere/aktualisiere Python-Abhängigkeiten..."
"$VENV_PYTHON" -m pip install --upgrade pip >/dev/null
"$VENV_PYTHON" -m pip install -r "$REQUIREMENTS_FILE"

STATE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/hardware-monitor-client"
mkdir -p "$STATE_DIR"
ENV_FILE="$STATE_DIR/agent.env"

cat > "$ENV_FILE" <<EOF
SERVER_URL=$SERVER_URL
SERVER_API_KEY=$API_KEY
AGENT_INTERVAL_SECONDS=$INTERVAL_SECONDS
EOF

chmod 600 "$ENV_FILE"
chmod +x "$RUNNER_SCRIPT"

SERVICE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
SERVICE_FILE="$SERVICE_DIR/${SERVICE_NAME}.service"
mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Hardware Monitor Client Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$REPO_ROOT
ExecStart=/usr/bin/env bash $RUNNER_SCRIPT $ENV_FILE $VENV_PYTHON $REPO_ROOT
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
  systemctl --user daemon-reload
  systemctl --user enable --now "${SERVICE_NAME}.service"
  echo "Hintergrunddienst eingerichtet: ${SERVICE_NAME}.service"
  echo "Status prüfen: systemctl --user status ${SERVICE_NAME}.service"
  echo "Entfernen: systemctl --user disable --now ${SERVICE_NAME}.service"
else
  LOG_FILE="$STATE_DIR/agent.log"
  nohup /usr/bin/env bash "$RUNNER_SCRIPT" "$ENV_FILE" "$VENV_PYTHON" "$REPO_ROOT" >> "$LOG_FILE" 2>&1 &
  echo "systemd --user nicht verfügbar. Agent wurde per nohup gestartet."
  echo "Log-Datei: $LOG_FILE"
fi
