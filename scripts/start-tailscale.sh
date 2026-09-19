#!/usr/bin/env bash
set -euo pipefail
umask 077

if ! command -v tailscale >/dev/null || ! command -v tailscaled >/dev/null; then
    echo 'Tailscale is missing. Run: bash scripts/install-tailscale.sh' >&2
    exit 1
fi

owa_state_dir="${XDG_DATA_HOME:-$HOME/.local/share}/tailscale"
owa_socket=/tmp/owa-tailscaled.sock
mkdir -p "$owa_state_dir"

# Serialize concurrent lifecycle/terminal starts. Do not pass the lock to the daemon.
exec 9>"$owa_state_dir/owa-start.lock"
flock -w 10 9
if ! tailscale --socket="$owa_socket" status --json >/dev/null 2>&1; then
    nohup setsid tailscaled --tun=userspace-networking \
        --socket="$owa_socket" --socks5-server=127.0.0.1:1055 \
        --state="$owa_state_dir/tailscaled.state" \
        >"$owa_state_dir/owa-tailscaled.log" 2>&1 </dev/null 9>&- &
    owa_daemon_pid=$!
    for attempt in {1..20}; do
        if tailscale --socket="$owa_socket" status --json >/dev/null 2>&1; then
            break
        fi
        if ! kill -0 "$owa_daemon_pid" 2>/dev/null; then
            echo "Tailscale failed to start. See $owa_state_dir/owa-tailscaled.log" >&2
            exit 1
        fi
        sleep 0.5
    done
fi

# Never block Codespaces startup on interactive authentication.
if tailscale --socket="$owa_socket" wait --timeout=10s >/dev/null 2>&1; then
    echo 'Tailscale ready. SOCKS5 proxy: 127.0.0.1:1055'
else
    echo "Tailscale is not connected. Inspect: tailscale --socket=$owa_socket status"
    echo "If login is needed, run: tailscale --socket=$owa_socket up"
fi
