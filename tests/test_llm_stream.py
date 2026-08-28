from app.llm.client import LLMClient


class FakeResponse:

    def raise_for_status(self):
        pass

    def iter_lines(self, decode_unicode=True):
        return [
            "data: {\"choices\":[{\"delta\":{\"content\":\"hello\"}}]}",
            "data: {\"choices\":[{\"delta\":{\"content\":\" world\"}}]}",
            "data: [DONE]",
        ]


class FakeSession:

    def post(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return FakeResponse()


def test_chat_stream_parses_openai_compatible_chunks():
    client = LLMClient()
    client.session = FakeSession()

    assert list(client.chat_stream([{"role": "user", "content": "hi"}])) == [
        "hello",
        " world",
    ]
    assert client.session.kwargs["stream"] is True
    assert client.session.kwargs["json"]["stream"] is True
