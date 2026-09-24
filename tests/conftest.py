import pytest


@pytest.fixture(autouse=True)
def isolate_agent_history(tmp_path, monkeypatch):
    """Unit tests must never load or overwrite the developer's conversation."""
    monkeypatch.setattr("app.agent.core.HISTORY_PATH", tmp_path / ".owa" / "history.json")
    monkeypatch.setenv("OWA_WRITE_APPROVAL", "allow")
    monkeypatch.setenv("OWA_COMMAND_SANDBOX", "host")
    from app.memory.episodes import EpisodeStore
    monkeypatch.setattr("app.agent.core.EpisodeStore", lambda _workspace: EpisodeStore(tmp_path))
