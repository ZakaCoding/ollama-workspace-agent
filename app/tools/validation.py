"""Argument validation for the flat string/integer schemas in the registry."""

import json


def validate_arguments(raw, schema: dict) -> dict:
    """Decode arguments without coercion; raise ValueError before tool execution."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, RecursionError) as exc:
            raise ValueError("arguments must be valid JSON") from exc
    if not isinstance(raw, dict):
        raise ValueError("arguments must be a JSON object")

    properties = schema.get("properties", {})
    missing = [key for key in schema.get("required", []) if key not in raw]
    if missing:
        raise ValueError(f"missing required arguments: {', '.join(missing)}")
    if any(key not in properties for key in raw):
        raise ValueError(
            "unexpected arguments; allowed arguments: "
            + (", ".join(properties) or "none")
        )
    types = {"string": str, "integer": int}
    for key, value in raw.items():
        expected = properties[key].get("type")
        # Exact types reject booleans as integers and never coerce model output.
        if expected not in types or type(value) is not types[expected]:
            raise ValueError(f"argument '{key}' must have type {expected}")
    return raw
