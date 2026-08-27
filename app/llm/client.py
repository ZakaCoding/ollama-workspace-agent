import json
import os

import requests


class LLMClient:
    def __init__(self):
        self.base_url = os.getenv(
            "LLM_BASE_URL",
            "http://localhost:11434/v1",
        ).rstrip("/")

        self.model = os.getenv(
            "LLM_MODEL",
            "ornith:9b",
        )

        self.session = requests.Session()

    def chat(self, messages, tools=None):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "required"

        print("\n>>> LLM REQUEST")
        print(f"URL   : {self.base_url}/chat/completions")
        print(f"MODEL : {self.model}")
        print(f"TOOLS : {len(tools or [])}")

        response = self.session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            timeout=300,
        )

        print(f"STATUS: {response.status_code}")

        if not response.ok:
            print(response.text)

        response.raise_for_status()

        data = response.json()
        message = data["choices"][0]["message"]

        print("TOOL CALLS:", len(message.get("tool_calls", [])))

        for call in message.get("tool_calls", []):
            print(
                "  ->",
                call["function"]["name"],
                call["function"].get("arguments"),
            )

        return data