import json
import os

import requests


class ApiClient:

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        session=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("API_KEY")
        self.session = session or requests.Session()

    def start(self):
        return self

    def close(self):
        self.session.close()

    def models(self):
        response = self.session.get(f"{self.base_url}/models", headers=self._headers(), timeout=10)
        response.raise_for_status()
        return response.json()

    def set_model(self, model):
        response = self.session.post(f"{self.base_url}/model", headers=self._headers(),
                                     json={"model": model}, timeout=10)
        response.raise_for_status()
        return response.json()

    def chat_events(self, message):
        response = self.session.post(f"{self.base_url}/chat/events", headers=self._headers(),
                                     json={"message": message}, timeout=(10, 300), stream=True)
        try:
            response.raise_for_status()
            response.encoding = "utf-8"
            done = False
            for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                if not line:
                    continue
                event = json.loads(line)
                if event["type"] == "error":
                    raise RuntimeError(event["message"])
                done = done or event["type"] == "done"
                yield event
            if not done:
                raise RuntimeError("Event stream ended before completion")
        finally:
            response.close()

    def _headers(self) -> dict[str, str]:
        if self.api_key:
            return {"X-API-Key": self.api_key}
        return {}

    def status(self) -> dict:
        response = self.session.get(
            f"{self.base_url}/status",
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def clear(self) -> None:
        response = self.session.post(
            f"{self.base_url}/clear",
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()

    def index(self, force: bool = False) -> dict:
        response = self.session.post(
            f"{self.base_url}/index" + ("?force=true" if force else ""),
            headers=self._headers(),
            timeout=300,
        )
        response.raise_for_status()
        return response.json()

    def chat_stream(self, message: str):
        response = self.session.post(
            f"{self.base_url}/chat/stream",
            headers=self._headers(),
            json={"message": message},
            timeout=300,
            stream=True,
        )
        try:
            response.raise_for_status()
            for chunk in response.iter_content(decode_unicode=True):
                if chunk:
                    yield chunk
        finally:
            close = getattr(response, "close", None)
            if close:
                close()
