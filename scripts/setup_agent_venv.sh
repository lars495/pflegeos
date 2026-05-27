#!/usr/bin/env bash
# Installiert die Python-Dependencies, die der Build-Agent auf dem Host braucht.
# User-local (~/.local), kein sudo nötig, kein venv (zur Sicherheit gegen
# fehlende python3-venv Pakete in Minimal-Images).
# Idempotent.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

pip3 install --user --quiet --break-system-packages \
  httpx==0.27.2 \
  redis==5.1.1 \
  pyyaml==6.0.2

# Sicherstellen dass ~/.local/bin im PATH ist (für eventuelle Tool-Binaries)
if ! grep -q '.local/bin' ~/.bashrc 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi

echo "[deps] ok"
python3 --version
python3 -c "import httpx, redis, yaml; print(f'httpx={httpx.__version__} redis={redis.__version__} pyyaml ok')"
