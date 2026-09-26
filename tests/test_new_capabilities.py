import json
import sqlite3
import sys
from types import SimpleNamespace

import pytest

from app.memory.episodes import EpisodeStore
from app.tools.filesystem import patch_file, write_file
from app.tools.mcp_bridge import MCPBridge
from app.tools.shell import run_command


def test_file_changes_denied_without_side_effects(tmp_path, monkeypatch):
    from app.tools import filesystem
    monkeypatch.setattr(filesystem, "WORKSPACE", tmp_path)
    monkeypatch.setenv("OWA_WRITE_APPROVAL", "deny")
    assert write_file("new.txt", "content") == "File change rejected by user."
    assert not (tmp_path / "new.txt").exists()
    (tmp_path / "existing.txt").write_text("before")
    assert patch_file("existing.txt", "before", "after") == "File change rejected by user."
    assert (tmp_path / "existing.txt").read_text() == "before"


def test_docker_command_has_resource_and_network_limits(monkeypatch, tmp_path):
    from app.tools import shell
    monkeypatch.setattr(shell, "WORKSPACE", tmp_path)
    monkeypatch.setenv("OWA_COMMAND_APPROVAL", "allow")
    monkeypatch.setenv("OWA_COMMAND_SANDBOX", "docker")
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(command=command, kwargs=kwargs)
        return SimpleNamespace(stdout="ok", stderr="", returncode=0)

    monkeypatch.setattr(shell.subprocess, "run", fake_run)
    assert "EXIT_CODE=0" in run_command("python -m pytest -q")
    command = captured["command"]
    assert command[:3] == ["docker", "run", "--rm"]
    assert command[command.index("--network") + 1] == "none"
    assert command[command.index("--pull") + 1] == "never"
    assert command[command.index("--pids-limit") + 1] == "128"
    assert command[-3:] == ["sh", "-lc", "python -m pytest -q"]
    assert captured["kwargs"]["shell"] is False


def test_command_denial_prevents_subprocess(monkeypatch):
    from app.tools import shell
    monkeypatch.setenv("OWA_COMMAND_APPROVAL", "deny")
    monkeypatch.setattr(shell.subprocess, "run", lambda *args, **kwargs: pytest.fail("executed"))
    assert run_command("python -m pytest -q") == "Command rejected by user."


def test_episodes_persist_only_changed_file_metadata(tmp_path):
    store = EpisodeStore(tmp_path)
    store.record("Fix parser", [], True)
    assert store.recent() == []
    store.record("Fix parser", ["app/parser.py"], True)
    restored = EpisodeStore(tmp_path).recent()
    assert len(restored) == 1
    assert restored[0]["files"] == ["app/parser.py"]
    assert restored[0]["verified"] is True


def test_corrupt_episode_database_does_not_stop_command_task(tmp_path, monkeypatch):
    from app.agent import core

    memory_dir = tmp_path / ".owa"
    memory_dir.mkdir()
    (memory_dir / "episodes.db").write_bytes(b"not a sqlite database")
    monkeypatch.setattr(core, "EpisodeStore", lambda _workspace: EpisodeStore(tmp_path))
    monkeypatch.setitem(core.FUNCTIONS, "run_command", lambda **kwargs: "EXIT_CODE=0")
    agent = core.Agent()
    replies = iter([
        {"tool_calls": [{"id": "run", "type": "function", "function": {
            "name": "run_command", "arguments": {"command": "python --version"},
        }}]},
        {"content": "The command completed."},
    ])
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: {"choices": [{"message": next(replies)}]})
    assert agent.run("Run python --version") == "The command completed."
    assert agent.state.completed


def test_memory_save_failure_preserves_completed_answer(monkeypatch):
    from app.agent import core

    class BrokenMemory:
        def recent(self):
            return []

        def record(self, *args):
            raise sqlite3.DatabaseError("storage failed")

    monkeypatch.setattr(core, "EpisodeStore", lambda _workspace: BrokenMemory())
    monkeypatch.setitem(core.FUNCTIONS, "write_file", lambda **kwargs: "Successfully wrote 2 characters to a.txt")
    monkeypatch.setitem(core.FUNCTIONS, "read_file", lambda **kwargs: "ok")
    agent = core.Agent()
    replies = iter([
        {"tool_calls": [{"id": "write", "type": "function", "function": {
            "name": "write_file", "arguments": {"path": "a.txt", "content": "ok"},
        }}]},
        {"tool_calls": [{"id": "read", "type": "function", "function": {
            "name": "read_file", "arguments": {"path": "a.txt"},
        }}]},
        {"content": "Created a.txt."},
    ])
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: {"choices": [{"message": next(replies)}]})
    assert agent.run("Create a.txt") == "Created a.txt."
    assert agent.state.completed


def test_mcp_bridge_lists_and_calls_configured_tools(tmp_path, monkeypatch):
    pytest.importorskip("jsonschema")
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({"mcpServers": {
        "demo": {"command": "python", "args": ["server.py"]},
    }}))
    bridge = MCPBridge(config)
    calls = []

    class Session:
        async def list_tools(self):
            return SimpleNamespace(tools=[SimpleNamespace(
                name="ping", description="Ping", inputSchema={"type": "object", "properties": {}})])

        async def call_tool(self, name, arguments):
            calls.append((name, arguments))
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="pong")],
                                   structuredContent=None, isError=False)

    async def fake_session(server, operation):
        assert server == "demo"
        return await operation(Session())

    monkeypatch.setattr(bridge, "_session", fake_session)
    monkeypatch.setenv("OWA_MCP_APPROVAL", "allow")
    definitions = bridge.list_tools()
    assert definitions[0]["function"]["name"] == "mcp__demo__ping"
    assert bridge.call("mcp__demo__ping", {}) == "pong"
    assert calls == [("ping", {})]


def test_mcp_call_denial_never_starts_server(tmp_path, monkeypatch):
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({"mcpServers": {"demo": {"command": "python"}}}))
    bridge = MCPBridge(config)
    bridge.routes["mcp__demo__ping"] = ("demo", "ping")
    monkeypatch.setenv("OWA_MCP_APPROVAL", "deny")
    monkeypatch.setitem(sys.modules, "jsonschema", None)
    assert bridge.call("mcp__demo__ping", {}) == "MCP tool call rejected by user."


def test_mcp_discovery_denial_never_starts_server(tmp_path, monkeypatch):
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({"mcpServers": {"demo": {"command": "python"}}}))
    bridge = MCPBridge(config)
    monkeypatch.setenv("OWA_MCP_APPROVAL", "deny")
    async def unexpected_session(*args):
        pytest.fail("MCP server was started")
    monkeypatch.setattr(bridge, "_session", unexpected_session)
    with pytest.raises(PermissionError, match="discovery rejected"):
        bridge.list_tools()


def test_tester_role_reviews_changed_file_without_tools(tmp_path, monkeypatch):
    from app.agent import delegation
    (tmp_path / "module.py").write_text("def add(a, b):\n    return a + b\n")
    evidence = []

    def fake_ask(role, task, content):
        evidence.append((role, task, content))
        return '{"pass": true, "issues": []}'

    monkeypatch.setattr(delegation, "_ask", fake_ask)
    assert delegation.tester_review("Fix add", ["module.py"], tmp_path) == (True, "")
    assert evidence[0][0] == "tester"
    assert "return a + b" in evidence[0][2]


def test_mcp_reference_stdio_server_round_trip(tmp_path, monkeypatch):
    pytest.importorskip("mcp")
    server = tmp_path / "server.py"
    server.write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "server = FastMCP('test')\n"
        "@server.tool()\n"
        "def ping(value: str) -> str:\n"
        "    return 'pong:' + value\n"
        "server.run(transport='stdio')\n"
    )
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({"mcpServers": {
        "local": {"command": sys.executable, "args": [str(server)]},
    }}))
    bridge = MCPBridge(config)
    monkeypatch.setenv("OWA_MCP_APPROVAL", "allow")
    definitions = bridge.list_tools()
    assert definitions[0]["function"]["name"] == "mcp__local__ping"
    assert "pong:hello" in bridge.call("mcp__local__ping", {"value": "hello"})


def test_agent_routes_explicit_mcp_inspection(monkeypatch):
    from app.agent import core

    class Bridge:
        servers = {"local": {}}
        error = None
        routes = {"mcp__local__ping": ("local", "ping")}

        def list_tools(self):
            return [{"type": "function", "function": {
                "name": "mcp__local__ping", "description": "Ping external service",
                "parameters": {"type": "object", "properties": {}},
            }}]

        def call(self, name, arguments):
            assert name == "mcp__local__ping" and arguments == {}
            return "pong"

    monkeypatch.setattr(core, "MCPBridge", Bridge)
    agent = core.Agent()
    replies = iter([
        {"tool_calls": [{"id": "1", "type": "function", "function": {
            "name": "mcp__local__ping", "arguments": "{}",
        }}]},
        {"content": "The service replied pong."},
    ])
    seen = []

    def chat(**kwargs):
        seen.append(kwargs)
        return {"choices": [{"message": next(replies)}]}

    monkeypatch.setattr(agent.llm, "chat", chat)
    assert agent.run("Use MCP to inspect the service.") == "The service replied pong."
    assert "mcp__local__ping" in {tool["function"]["name"] for tool in seen[0]["tools"]}


def test_mcp_tools_are_not_exposed_on_later_greetings_or_unrelated_actions(monkeypatch):
    from app.agent import core

    class Bridge:
        servers = {"local": {}}
        error = None
        routes = {"mcp__local__ping": ("local", "ping")}

        def list_tools(self):
            return [{"type": "function", "function": {
                "name": "mcp__local__ping", "description": "Ping",
                "parameters": {"type": "object", "properties": {}},
            }}]

        def call(self, name, arguments):
            return "pong"

    monkeypatch.setattr(core, "MCPBridge", Bridge)
    monkeypatch.setitem(core.FUNCTIONS, "run_command", lambda **kwargs: "EXIT_CODE=0")
    agent = core.Agent()
    replies = iter([
        {"tool_calls": [{"id": "mcp", "type": "function", "function": {
            "name": "mcp__local__ping", "arguments": "{}",
        }}]},
        {"content": "pong"},
        {"content": "Hello!"},
        {"tool_calls": [{"id": "run", "type": "function", "function": {
            "name": "run_command", "arguments": {"command": "python --version"},
        }}]},
        {"content": "The command completed."},
    ])
    tool_names = []

    def chat(**kwargs):
        tool_names.append({tool["function"]["name"] for tool in kwargs["tools"]})
        return {"choices": [{"message": next(replies)}]}

    monkeypatch.setattr(agent.llm, "chat", chat)
    assert agent.run("Use MCP to inspect the service") == "pong"
    assert agent.run("hello") == "Hello!"
    assert agent.run("Run python --version") == "The command completed."
    assert "mcp__local__ping" in tool_names[0]
    assert "mcp__local__ping" not in tool_names[2]
    assert "mcp__local__ping" not in tool_names[3]


def test_unrelated_action_never_starts_configured_mcp_server(monkeypatch):
    from app.agent import core

    class Bridge:
        servers = {"local": {}}
        error = None
        routes = {}

        def list_tools(self):
            pytest.fail("MCP discovery started for an unrelated task")

    monkeypatch.setattr(core, "MCPBridge", Bridge)
    monkeypatch.setitem(core.FUNCTIONS, "run_command", lambda **kwargs: "EXIT_CODE=0")
    agent = core.Agent()
    replies = iter([
        {"tool_calls": [{"id": "run", "type": "function", "function": {
            "name": "run_command", "arguments": {"command": "python --version"},
        }}]},
        {"content": "The command completed."},
    ])
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: {"choices": [{"message": next(replies)}]})
    assert agent.run("Run python --version") == "The command completed."


def test_optional_manager_and_tester_wrap_coder_loop(monkeypatch):
    from app.agent import core, delegation

    monkeypatch.setattr(delegation, "enabled", lambda: True)
    monkeypatch.setattr(delegation, "manager_plan", lambda task: "Create and verify the file.")
    reviews = []
    monkeypatch.setattr(delegation, "tester_review", lambda *args: reviews.append(args) or (True, ""))
    monkeypatch.setitem(core.FUNCTIONS, "write_file", lambda **kwargs: "Successfully wrote 2 characters to a.txt")
    monkeypatch.setitem(core.FUNCTIONS, "read_file", lambda **kwargs: "ok")
    agent = core.Agent()
    replies = iter([
        {"tool_calls": [{"id": "write", "type": "function", "function": {
            "name": "write_file", "arguments": {"path": "a.txt", "content": "ok"},
        }}]},
        {"tool_calls": [{"id": "read", "type": "function", "function": {
            "name": "read_file", "arguments": {"path": "a.txt"},
        }}]},
        {"content": "Created and verified a.txt."},
    ])
    prompts = []

    def chat(**kwargs):
        prompts.append(kwargs["messages"])
        return {"choices": [{"message": next(replies)}]}

    monkeypatch.setattr(agent.llm, "chat", chat)
    assert agent.run("Create a.txt") == "Created and verified a.txt."
    assert reviews and reviews[0][1] == ["a.txt"]
    assert any("Manager plan" in msg.get("content", "") for msg in prompts[0])
