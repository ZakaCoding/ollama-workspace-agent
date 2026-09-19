#!/usr/bin/env bash
set -euo pipefail

owa_repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
bash "$owa_repo/scripts/start-tailscale.sh"
export ALL_PROXY=socks5h://127.0.0.1:1055
if [[ -x "$owa_repo/.venv312/bin/python" ]]; then
    exec "$owa_repo/.venv312/bin/python" "$owa_repo/main.py" "$@"
elif [[ -x "$owa_repo/.venv/bin/python" ]]; then
    exec "$owa_repo/.venv/bin/python" "$owa_repo/main.py" "$@"
else
    exec python3 "$owa_repo/main.py" "$@"
fi
