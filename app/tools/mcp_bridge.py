"""Optional MCP stdio tools configured by the operator, outside the workspace.

Install OwA with ``[mcp]`` and place server definitions in
``~/.config/owa/mcp.json``. Each call reconnects so no background process
survives a request or shares state across workspaces.
"""

import json
import re
from pathlib import Path

from app.config import CONFIG_DIR
from app.tools.approval import approve


class MCPBridge:
    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or CONFIG_DIR / "mcp.json"
        self.error = None
        try:
            self.servers = self._read_config()
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            self.servers = {}
            self.error = f"Invalid MCP configuration: {exc}"
        self.routes: dict[str, tuple[str, str]] = {}
        self.schemas: dict[str, dict] = {}

    def _read_config(self) -> dict:
        if not self.config_path.exists():
            return {}
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("MCP configuration must be an object")
        servers = data.get("mcpServers", {})
        if not isinstance(servers, dict):
            raise ValueError("mcpServers must be an object")
        for name, entry in servers.items():
            if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
                raise ValueError("MCP server names must be alphanumeric")
            if (not isinstance(entry, dict) or not isinstance(entry.get("command"), str)
                    or not isinstance(entry.get("args", []), list)
                    or not all(isinstance(arg, str) for arg in entry.get("args", []))):
                raise ValueError(f"Invalid MCP server configuration: {name}")
        return servers

    async def _session(self, server: str, operation):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        entry = self.servers[server]
        params = StdioServerParameters(
            command=entry["command"], args=entry.get("args", []),
            env=entry.get("env"),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await operation(session)

    def list_tools(self) -> list[dict]:
        if not self.servers:
            return []
        import anyio

        self.routes.clear()
        self.schemas.clear()

        async def discover(server, session):
            return (await session.list_tools()).tools

        definitions = []
        for server in self.servers:
            entry = self.servers[server]
            command = json.dumps([entry["command"], *entry.get("args", [])], ensure_ascii=False)
            if not approve("MCP server discovery", f"{server}: {command}",
                           variable="OWA_MCP_APPROVAL"):
                raise PermissionError(f"MCP server discovery rejected by user: {server}")
            try:
                async def fetch():
                    with anyio.fail_after(30):
                        return await self._session(server, lambda session: discover(server, session))
                tools = anyio.run(fetch)
            except Exception as exc:
                raise RuntimeError(f"MCP server {server} could not be listed: {exc}") from exc
            for tool in tools:
                name = f"mcp__{server}__{tool.name}"
                if name in self.routes:
                    continue
                self.routes[name] = (server, tool.name)
                self.schemas[name] = tool.inputSchema if isinstance(tool.inputSchema, dict) else {"type": "object"}
                definitions.append({"type": "function", "function": {
                    "name": name,
                    "description": tool.description or f"MCP tool {tool.name} from {server}",
                    "parameters": tool.inputSchema if isinstance(tool.inputSchema, dict) else {"type": "object", "properties": {}},
                }})
        return definitions

    def call(self, name: str, arguments: dict) -> str:
        server, tool = self.routes[name]
        if not approve("MCP tool call", f"{server}/{tool}: {json.dumps(arguments, ensure_ascii=False)[:1000]}",
                       variable="OWA_MCP_APPROVAL"):
            return "MCP tool call rejected by user."

        import anyio
        from jsonschema import ValidationError, validate

        try:
            validate(arguments, self.schemas.get(name, {"type": "object"}))
        except ValidationError as exc:
            return f"MCP tool error: invalid arguments: {exc.message}"

        async def invoke(session):
            return await session.call_tool(tool, arguments)

        async def execute():
            with anyio.fail_after(120):
                return await self._session(server, invoke)
        result = anyio.run(execute)
        parts = [block.text for block in result.content if getattr(block, "type", None) == "text"]
        if result.structuredContent is not None:
            parts.append(json.dumps(result.structuredContent, ensure_ascii=False))
        output = "\n".join(parts)[:30000]
        return ("MCP tool error: " if result.isError else "") + output
