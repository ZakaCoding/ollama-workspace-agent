from app.api_client import ApiClient


class FakeResponse:

    def __init__(self, data=None, chunks=None):
        self.data = data
        self.chunks = chunks or []

    def raise_for_status(self):
        pass

    def json(self):
        return self.data

    def iter_content(self, decode_unicode=True):
        return self.chunks


class FakeSession:

    def __init__(self):
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append(("get", args, kwargs))
        return FakeResponse({"ready": True, "chunks": 2})

    def post(self, *args, **kwargs):
        self.calls.append(("post", args, kwargs))
        if args[0].endswith("/chat/stream"):
            return FakeResponse(chunks=["hello", " world"])
        return FakeResponse({"status": "ok"})


def test_api_client_forwards_key_and_streams_chat():
    session = FakeSession()
    client = ApiClient(
        "http://localhost:8000/",
        api_key="secret",
        session=session,
    )

    assert list(client.chat_stream("hello")) == ["hello", " world"]
    method, args, kwargs = session.calls[0]
    assert method == "post"
    assert args[0] == "http://localhost:8000/chat/stream"
    assert kwargs["headers"] == {"X-API-Key": "secret"}
    assert kwargs["json"] == {"message": "hello"}
    assert kwargs["stream"] is True


def test_api_client_supports_status_clear_and_index():
    session = FakeSession()
    client = ApiClient("http://localhost:8000", session=session)

    assert client.status() == {"ready": True, "chunks": 2}
    client.clear()
    assert client.index() == {"status": "ok"}
    assert [call[0] for call in session.calls] == ["get", "post", "post"]
