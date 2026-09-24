# Agent development plan

## Implemented in this iteration

1. Keep Ollama's native structured tool calls as the primary route; retain the
   narrow JSON text adapter for models that fail to emit a native call.
2. Gate file writes, shell commands, and MCP tool calls. Shell commands use a
   Docker sandbox by default with no network and a bounded process, CPU, and
   memory budget. Host execution requires an explicit setting.
3. Discover configured MCP stdio tools and route calls through the normal agent
   tool loop. Server configuration lives outside the workspace.
4. Record completed file-change episodes in a local SQLite database and include
   a small recent excerpt in later action prompts.
5. Offer optional manager, coder, and tester roles. The manager and tester use
   separate read-only model calls; the coder retains the existing tool loop.

## Next milestones

1. **Sandbox profiles:** support language-specific local images, workspace
   mounts with narrower write scope, and interactive approval through the HTTP
   API instead of a terminal prompt in the server process.
2. **MCP interoperability:** support resources, prompts, HTTP transport,
   paginated tool lists, server change notifications, and richer JSON Schema
   validation. Add live integration tests against a reference MCP server.
3. **Memory control:** add explicit commands to inspect, search, delete, and
   export episodes. Add retention limits and opt-in summaries that distinguish
   verified facts from past task descriptions.
4. **Delegation quality:** give the tester a structured patch/diff and targeted
   test output, rerun review after fixes, and benchmark single-agent against
   delegated execution before enabling it by default.
5. **Reliability gate:** run the existing small-model evaluation suite for each
   role configuration and record completion rate, latency, command approvals,
   and incorrect-edit rate before a release.
