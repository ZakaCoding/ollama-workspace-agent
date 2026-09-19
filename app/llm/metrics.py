"""Bounded, in-memory measurements; never retain prompts or response content."""

from threading import Lock


def _token_count(usage: dict, key: str) -> int | None:
    value = usage.get(key)
    return value if type(value) is int and value >= 0 else None


class LLMMetrics:
    def __init__(self):
        self._lock = Lock()
        self._requests = 0
        self._failed_requests = 0
        self._total_duration_ms = 0.0
        self._prompt_tokens = 0
        self._completion_tokens = 0
        self._requests_with_usage = 0
        self._last_request = None

    def record(self, *, model: str, streaming: bool, succeeded: bool,
               duration_ms: float, usage=None):
        usage = usage if isinstance(usage, dict) else {}
        prompt_tokens = _token_count(usage, "prompt_tokens")
        completion_tokens = _token_count(usage, "completion_tokens")
        with self._lock:
            self._requests += 1
            self._failed_requests += int(not succeeded)
            self._total_duration_ms += duration_ms
            self._prompt_tokens += prompt_tokens or 0
            self._completion_tokens += completion_tokens or 0
            self._requests_with_usage += int(
                prompt_tokens is not None and completion_tokens is not None
            )
            self._last_request = {
                "model": model,
                "streaming": streaming,
                "succeeded": succeeded,
                "duration_ms": round(duration_ms, 2),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "requests": self._requests,
                "failed_requests": self._failed_requests,
                "total_duration_ms": round(self._total_duration_ms, 2),
                "prompt_tokens": self._prompt_tokens,
                "completion_tokens": self._completion_tokens,
                "requests_with_usage": self._requests_with_usage,
                "last_request": dict(self._last_request) if self._last_request else None,
            }
