import sqlite3

from app.service import AgentService


class FakeAgent:

    def __init__(self):
        self.messages = []
        self.cleared = False

    def run(self, message):
        self.messages.append(message)
        return "reply"

    def clear(self):
        self.cleared = True


def test_service_delegates_chat_and_clear(tmp_path):
    agent = FakeAgent()
    service = AgentService(tmp_path, agent)

    assert service.chat("hello") == "reply"
    assert agent.messages == ["hello"]

    service.clear()
    assert agent.cleared


def test_service_reports_missing_index(tmp_path):
    service = AgentService(tmp_path, FakeAgent())

    assert service.status() == {"ready": False, "chunks": 0}


def test_service_reports_index_chunk_count(tmp_path):
    index_path = tmp_path / ".ai" / "index.db"
    index_path.parent.mkdir()
    with sqlite3.connect(index_path) as db:
        db.execute(
            "CREATE TABLE documents (id INTEGER, content TEXT)"
        )
        db.executemany(
            "INSERT INTO documents VALUES (?, ?)",
            [(1, "one"), (2, "two")],
        )

    service = AgentService(tmp_path, FakeAgent())

    assert service.status() == {"ready": True, "chunks": 2}
