#!/usr/bin/env bash
set -euo pipefail

if command -v tailscale >/dev/null && command -v tailscaled >/dev/null; then
    exit 0
fi

# Official installer configures the package repository for this distribution.
installer=$(mktemp /tmp/owa-tailscale-install.XXXXXX)
trap 'rm -f -- "$installer"' EXIT
curl --fail --silent --show-error --location --max-time 60 \
    https://tailscale.com/install.sh -o "$installer"
sudo sh "$installer"
