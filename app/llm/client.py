import json
import os
from time import perf_counter

import requests

from app.config import max_output_tokens
from app.llm.metrics import LLMMetrics


class IncompleteStreamError(RuntimeError):
    """Raised when Ollama ends a stream without a complete response."""


class LLMClient:
    def __init__(self):
        self.base_url = os.getenv(
            "LLM_BASE_URL",
            "http://localhost:11434/v1",
        ).rstrip("/")
        self.session = requests.Session()
        self.metrics = LLMMetrics()

    @property
    def model(self):
        return os.getenv("LLM_MODEL", "ornith:9b")

    def model_metadata(self) -> dict:
        """Read optional Ollama metadata without loading or generating with a model."""
        metadata = {"capabilities": None, "model_context_tokens": None}
        # Remove only the compatibility API suffix, preserving proxy prefixes.
        url = self.base_url.removesuffix("/v1") + "/api/show"
        try:
            response = self.session.post(url, json={"model": self.model}, timeout=2)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            return metadata
        if not isinstance(data, dict):
            return metadata

        capabilities = data.get("capabilities")
        if isinstance(capabilities, list) and all(isinstance(c, str) for c in capabilities):
            metadata["capabilities"] = capabilities
        info = data.get("model_info")
        if isinstance(info, dict):
            architecture = info.get("general.architecture")
            context = info.get(f"{architecture}.context_length")
            if type(context) is int and context > 0:
                metadata["model_context_tokens"] = context
        return metadata

    def chat(self, messages, tools=None):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "max_tokens": max_output_tokens(),
            "temperature": 0,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        started = perf_counter()
        succeeded = False
        usage = None
        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=300,
            )
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage") if isinstance(data, dict) else None
            succeeded = True
            return data
        finally:
            self.metrics.record(
                model=payload["model"], streaming=False, succeeded=succeeded,
                duration_ms=(perf_counter() - started) * 1000, usage=usage,
            )

    def chat_stream(self, messages):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "max_tokens": max_output_tokens(),
            "temperature": 0,
        }

        started = perf_counter()
        response = None
        usage = None
        completed = False
        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=(10, 60),
                stream=True,
            )
            response.raise_for_status()
            response.encoding = "utf-8"

            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue

                data = line[5:].strip()
                if data == "[DONE]":
                    completed = True
                    break

                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if not isinstance(chunk, dict):
                    continue
                # Usage can arrive in a final event with no choices.
                if isinstance(chunk.get("usage"), dict):
                    usage = chunk["usage"]
                choices = chunk.get("choices", [])
                if not choices:
                    continue

                delta = choices[0].get("delta", {})
                finish_reason = choices[0].get("finish_reason")
                if finish_reason and finish_reason != "stop":
                    raise IncompleteStreamError(
                        f"Model stream ended with finish reason: {finish_reason}"
                    )

                content = delta.get("content")
                if content:
                    yield content

            if not completed:
                raise IncompleteStreamError("Model stream ended before [DONE].")
        finally:
            try:
                if response is not None:
                    response.close()
            finally:
                self.metrics.record(
                    model=payload["model"], streaming=True, succeeded=completed,
                    duration_ms=(perf_counter() - started) * 1000, usage=usage,
                )
