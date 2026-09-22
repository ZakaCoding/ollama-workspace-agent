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


def load_config(workspace: Path | None = None):
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)
    load_dotenv((workspace or Path.cwd()) / ".env", override=True)


def configuration_warnings() -> list[str]:
    """Explain fallbacks without exposing URLs, credentials, or environment values."""
    from urllib.parse import urlsplit
    warnings = []
    for name, minimum, maximum in (
        ("OWA_CONTEXT_TOKENS", 2048, 262144),
        ("OWA_MAX_OUTPUT_TOKENS", 128, 16384),
    ):
        raw = os.getenv(name)
        if raw is None:
            continue
        try:
            value = int(raw)
        except ValueError:
            warnings.append(f"{name} is not an integer; using the default.")
            continue
        if not minimum <= value <= maximum:
            warnings.append(f"{name} is outside {minimum}–{maximum}; using the nearest bound.")
    for name in ("LLM_BASE_URL", "EMBEDDING_BASE_URL"):
        raw = os.getenv(name)
        if raw:
            try:
                url = urlsplit(raw)
                valid = url.scheme in {"http", "https"} and bool(url.hostname)
            except ValueError:
                valid = False
            if not valid:
                warnings.append(f"{name} must be an HTTP or HTTPS URL with a host.")
    return warnings
