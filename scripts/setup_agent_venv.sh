#!/usr/bin/env bash
# Erstellt .venv-agent/ mit den Dependencies, die der Build-Agent auf dem Host braucht.
# Idempotent.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv-agent ]]; then
  python3 -m venv .venv-agent
fi

.venv-agent/bin/pip install --quiet --upgrade pip
.venv-agent/bin/pip install --quiet \
  httpx==0.27.2 \
  redis==5.1.1 \
  pyyaml==6.0.2

echo "[venv] ready at .venv-agent/"
.venv-agent/bin/python --version
.venv-agent/bin/python -c "import httpx, redis, yaml; print('deps ok:', httpx.__version__, redis.__version__)"
