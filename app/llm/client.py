import json
import os

import requests

from app.config import max_output_tokens


class IncompleteStreamError(RuntimeError):
    """Raised when Ollama ends a stream without a complete response."""


class LLMClient:
    def __init__(self):
        self.base_url = os.getenv(
            "LLM_BASE_URL",
            "http://localhost:11434/v1",
        ).rstrip("/")
        self.session = requests.Session()

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
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        response = self.session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=300,
        )
        response.raise_for_status()
        return response.json()

    def chat_stream(self, messages):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": max_output_tokens(),
        }

        response = self.session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=(10, 60),
            stream=True,
        )
        response.raise_for_status()
        response.encoding = "utf-8"

        completed = False

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
