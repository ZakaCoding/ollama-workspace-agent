import pytest


@pytest.fixture(autouse=True)
def isolate_agent_history(tmp_path, monkeypatch):
    """Unit tests must never load or overwrite the developer's conversation."""
    monkeypatch.setattr("app.agent.core.HISTORY_PATH", tmp_path / ".owa" / "history.json")
