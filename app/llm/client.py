import json
import os

import requests


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

    def chat(self, messages, tools=None):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
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
        }

        response = self.session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=(10, 60),
            stream=True,
        )
        response.raise_for_status()

        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue

            data = line[5:].strip()
            if data == "[DONE]":
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
                # Model stopped for a non-content reason (tool_call, length, etc.)
                # Signal empty so caller can fall back to non-streaming
                return

            content = delta.get("content")
            if content:
                yield content