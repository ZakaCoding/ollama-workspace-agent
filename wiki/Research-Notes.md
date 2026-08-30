# Research Notes

OwA is also a useful testbed for studying how coding agents behave in realistic local workflows. The project is intentionally compact, which makes it easy to evaluate tool use, retrieval quality, and verification behavior in a reproducible way.

## Research questions worth exploring

### Tool selection and planning

When does the model choose `search_code` before reading individual files? This is a good question for comparing retrieval-first and read-first behaviors across a set of coding tasks.

### Retrieval quality

The indexer is simple but useful. A strong research direction is to compare semantic retrieval, keyword fallback, and hybrid ranking on a fixed set of tasks with known relevant files.

### Verification behavior

A key question is whether the agent verifies its own edits before claiming they are complete. This is especially important for generated patches, tests, and refactors.

### Human approval patterns

The confirmation flow is an important safety design element. Studies can examine how often users approve or reject shell or write actions, and how that impacts completion rates and trust.

### Workspace isolation

Because the project works inside a repository, it is a useful environment for checking how well task state, files, and tool results stay separated across interactions.

## Good evaluation record

For each run, track:

- repo revision
- model name and settings
- task prompt
- tool sequence and arguments
- files read or modified
- tests run and exit codes
- user approval or rejection events
- final outcome and reviewer notes

This gives a much better picture of performance than a single demo screenshot or a successful chat snippet.

## Current limitations

- there is no large benchmark suite yet
- local models vary in quality and latency
- retrieval quality depends on the embedding model chosen
- the current indexing design is simple by design
- the test suite is still modest compared with a full product surface

## Reproducibility guidance

Public experiments should:

- pin the repo revision
- record the Ollama model names used
- avoid leaking secrets or private source content
- publish the prompts and scoring rules when possible
- save logs with sensitive values redacted

## Possible roadmap

- add a benchmark harness for repo tasks
- improve retrieval quality with hybrid scoring
- add stale chunk cleanup for the local index
- add stronger validation and test-oriented verification steps
- add optional mock or deterministic LLM testing paths
- expand documentation for safe and repeatable local usage
