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

    def index(self) -> dict:
        response = self.session.post(
            f"{self.base_url}/index",
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
        response.raise_for_status()
        for chunk in response.iter_content(decode_unicode=True):
            if chunk:
                yield chunk
