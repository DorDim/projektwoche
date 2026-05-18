#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <env-file> <python-executable> <repo-root>" >&2
  exit 1
fi

ENV_FILE="$1"
PYTHON_EXECUTABLE="$2"
REPO_ROOT="$3"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env-Datei nicht gefunden: $ENV_FILE" >&2
  exit 1
fi

if [[ ! -x "$PYTHON_EXECUTABLE" ]]; then
  echo "Python-Executable nicht gefunden: $PYTHON_EXECUTABLE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

export CLIENT_ID_FILE="$REPO_ROOT/.client_id"
cd "$REPO_ROOT"
exec "$PYTHON_EXECUTABLE" -m client.agent
