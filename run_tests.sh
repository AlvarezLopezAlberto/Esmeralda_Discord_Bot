#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
PYTHON="$VENV/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "Virtualenv not found. Creating at $VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -r "$ROOT/requirements.txt"
fi

"$PYTHON" -m unittest discover -s "$ROOT/tests"
