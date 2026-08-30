from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "owa"
ENV_PATH = CONFIG_DIR / ".env"


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
