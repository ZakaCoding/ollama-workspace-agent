import os
from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "owa"
ENV_PATH = CONFIG_DIR / ".env"


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def bounded_int_env(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    """Read an integer setting without allowing unsafe resource values."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return min(max(value, minimum), maximum)


def context_window_tokens() -> int:
    """Return the context budget used for retrieved repository evidence."""
    return bounded_int_env(
        "OWA_CONTEXT_TOKENS",
        default=8192,
        minimum=2048,
        maximum=262144,
    )


def max_output_tokens() -> int:
    """Return the maximum response size sent to the chat model."""
    return bounded_int_env(
        "OWA_MAX_OUTPUT_TOKENS",
        default=1024,
        minimum=128,
        maximum=16384,
    )
