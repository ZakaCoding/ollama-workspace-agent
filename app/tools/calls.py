"""Narrow compatibility adapter for models returning JSON tool calls as text."""

import json
import re


def parse_text_answer(content: str | None) -> str | None:
    """Recognize the explicit finish action in the text-only protocol."""
    if not isinstance(content, str):
        return None
    try:
        value = json.loads(content)
    except ValueError:
        return None
    if (isinstance(value, dict) and set(value) == {"answer"}
            and isinstance(value["answer"], str) and value["answer"].strip()):
        return value["answer"]
    return None


def parse_text_tool_call(content: str | None, sequence: int) -> dict | None:
    if not isinstance(content, str):
        return None
    raw = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1)
    # Qwen-family templates may leak their tool envelope into content. Only a
    # complete JSON call inside it qualifies, never a reported command result.
    envelope = re.fullmatch(r"<(tool_call|tool_response)>\s*(.*?)\s*</\1>", raw, re.DOTALL)
    if envelope:
        raw = envelope.group(2)
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict) or set(value) != {"name", "arguments"}:
        return None
    if not isinstance(value["name"], str):
        return None
    return {
        "id": f"text_call_{sequence}", "type": "function",
        "function": {"name": value["name"], "arguments": json.dumps(value["arguments"])},
    }
