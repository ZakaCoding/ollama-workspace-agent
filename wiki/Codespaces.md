# Codespaces and Tailscale

The dev container configuration installs Tailscale when needed and runs
`scripts/start-tailscale.sh` on each container start. The startup script runs
the daemon in userspace mode, in a detached process session, with a SOCKS5
proxy listening only on `127.0.0.1:1055`. It is safe to run repeatedly.

If adding this configuration to an existing Codespace, rebuild the container
to apply its lifecycle hooks. You can start it immediately without rebuilding:

```bash
bash scripts/install-tailscale.sh
bash scripts/start-tailscale.sh
```

Tailscale device state is kept in `${XDG_DATA_HOME:-$HOME/.local/share}/tailscale`,
outside the repository. An existing login is reused. On a new Codespace, after
a rebuild that removes home-directory state, or when reauthentication is
required, run this command and open its login link:

```bash
tailscale --socket=/tmp/owa-tailscaled.sock up
```

Startup does not wait indefinitely for login. It prints diagnostic commands
if the device cannot connect. Daemon logs are stored as `owa-tailscaled.log`
in the state directory. The installation script uses Tailscale's official
installer and needs sudo if the binaries are not already installed.

## Run OwA through Tailscale

Configure your Ollama host and models using `/setup` or a private project `.env`,
then launch from the workspace you want OwA to operate on:

```bash
bash scripts/owa-tailscale.sh
```

The launcher starts Tailscale if necessary and sets
`ALL_PROXY=socks5h://127.0.0.1:1055` for OwA. It prefers this repository's
`.venv312`, then `.venv`, then `python3`. Install the project dependencies in
the selected environment first. It leaves the caller's working directory and
shell environment unchanged. Existing `HTTP_PROXY`, `HTTPS_PROXY`, and
`NO_PROXY` settings still follow the HTTP libraries' normal precedence.

Inspect connectivity:

```bash
tailscale --socket=/tmp/owa-tailscaled.sock status
curl --max-time 10 --proxy socks5h://127.0.0.1:1055 http://YOUR_TAILSCALE_HOST:11434/api/tags
```

For background, see [Tailscale userspace networking](https://tailscale.com/docs/concepts/userspace-networking)
and [GitHub dev containers](https://docs.github.com/en/codespaces/setting-up-your-project-for-codespaces/adding-a-dev-container-configuration/introduction-to-dev-containers).
