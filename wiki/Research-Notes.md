# Research Notes

This page frames the repository as a small, reproducible environment for public research into coding agents. It describes the current implementation and proposes experiments; proposed work is not presented as implemented behavior.

## Questions worth studying

### Tool selection

When does a model choose `search_code` before opening individual files? Measure tool order, number of calls, task completion, and irrelevant retrievals across tasks with and without semantic search instructions.

### Retrieval quality

Create a benchmark of questions mapped to expected files and symbols. Compare embedding-only ranking, keyword fallback, and hybrid scoring. Report recall at several result limits instead of judging one successful demo.

### Verification

Compare outcomes when the agent is asked to verify its work versus when it receives no verification instruction. Record test execution, detected failures, unnecessary calls, and false claims of completion.

### State isolation

Run interleaved tasks and test whether requirements or observations from one task appear in another. Fresh `AgentState` per request provides a baseline for this experiment.

### Human approval

Measure how confirmation prompts affect completion time, rejected operations, and unsafe-operation prevention. A useful study should include both benign and destructive-looking commands.

## Suggested evaluation record

For every run, preserve:

- repository revision
- model name and temperature or equivalent settings
- task prompt
- available tools
- tool-call sequence
- tool arguments and results, with secrets redacted
- files changed
- tests run and exit codes
- human interventions
- final outcome and reviewer judgment

## Live self-run narrative

A particularly useful research artifact is the repository's own self-hosted session: running OwA from inside the project and asking it to explain what it is, where it is running, and how the indexing/search loop behaves.

This is documented in [../JOURNEY.md](../JOURNEY.md). It is not a synthetic demo; it is a real end-to-end session in which the agent is both the subject and the tool. The conversation captures a practical local validation loop:

- the agent indexes the repository itself
- it answers questions about the project using the current workspace as context
- it explains its capabilities and limitations in plain language
- it demonstrates context management and search behavior under realistic conditions

This pattern is relevant to research because it gives a reproducible way to study the agent's behavior without needing a separate test harness or cloud environment. It also makes the limitations visible in a way that a scripted benchmark often does not: the agent is being observed in a real, human-centered session.

The main value here is not that the model is "smart" in a broad sense, but that it can operate within a real workspace using only local tooling. That is a meaningful experiment in tool-using coding agents.

## Current limitations

- There is no formal benchmark suite.
- The agent depends on a remote model service.
- Search quality depends on the selected embedding model.
- Vector storage and ranking are intentionally simple.
- Prompt constraints can be bypassed by model mistakes or conflicting tool results.
- The current test suite is narrow and does not exercise the live LLM loop.

## Reproducibility

Public experiments should pin the repository revision, record environment variables without secrets, describe the Ollama models, and publish task sets and scoring scripts where possible. Do not publish private source files, credentials, or raw logs containing sensitive content.

## Possible roadmap

- Add a real dependency configuration and repeatable CI workflow.
- Add an indexer CLI with rebuild and cleanup commands.
- Add stale-chunk removal and index metadata for embedding-model compatibility.
- Add hybrid retrieval and repository-aware filters.
- Add structured tool-result types and stronger argument validation.
- Add approval policies for writes and shell commands.
- Add end-to-end tests using a deterministic mock LLM.
- Add benchmark tasks for retrieval, editing, and verification.
