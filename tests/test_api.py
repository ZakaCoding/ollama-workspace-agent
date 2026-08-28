from fastapi.testclient import TestClient

from app.api import create_app


class FakeAgent:

    def __init__(self):
        self.messages = []

    def run(self, message):
        self.messages.append(message)
        return "reply"

    def clear(self):
        pass


class FakeService:

    def __init__(self):
        self.agent = FakeAgent()
        self.indexed = False

    def chat(self, message):
        return self.agent.run(message)

    def status(self):
        return {"ready": self.indexed, "chunks": 3 if self.indexed else 0}

    def index(self):
        self.indexed = True


def test_health_and_status_endpoints():
    client = TestClient(create_app(FakeService()))

    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/status").json() == {"ready": False, "chunks": 0}


def test_chat_endpoint_delegates_to_service():
    service = FakeService()
    client = TestClient(create_app(service))

    response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert response.json() == {"content": "reply", "completed": True}
    assert service.agent.messages == ["hello"]


def test_chat_endpoint_rejects_empty_messages():
    client = TestClient(create_app(FakeService()))

    response = client.post("/chat", json={"message": ""})

    assert response.status_code == 422


def test_index_endpoint_runs_indexing_and_returns_status():
    service = FakeService()
    client = TestClient(create_app(service))

    response = client.post("/index")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "ready": True,
        "chunks": 3,
    }
