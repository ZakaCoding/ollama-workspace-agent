# Reviewed workspace lessons

This opt-in first step adds durable lessons without another model or embedding index.
It is a review workflow, not an OS security boundary. Any process with write access
to `.owa/lessons.db` can tamper with it, including an agent allowed to run arbitrary
host commands. Keep command approval enabled and treat every recalled lesson as
untrusted data. Review never grants tool permissions.

From the workspace root, using the Python environment containing OwA:

```sh
python -m app.memory propose "Run the parser regression tests after changing token handling" --source "commit abc123; parser regression passed"
python -m app.memory list
python -m app.memory approve 1
export OWA_LESSON_MEMORY=1
owa
```

Use `python -m app.memory reject 1` for a pending candidate, or
`python -m app.memory revoke 1` for an approved lesson. `--workspace PATH`
may be placed before the subcommand. IDs are local to each workspace.
List output includes full content, source, state, and review timestamps.
The source is user-supplied provenance, not automatically verified evidence.

Candidates remain pending until explicitly approved. Review commands are not
registered as model tools. No automatic lesson extraction or promotion is added.
Existing episode metadata remains unchanged and is separate from reviewed lessons.

Recall is disabled by default. When enabled, the three newest approved lessons
are included only on the tool/action route, with an additional cap of 2,500 characters (whole records only).
Social chat and evidence-only repository answers do not use them. Recalled
lessons are never saved into conversation history, and revocations take effect
on the next model request. This cannot erase a model's previous responses or undo
an action. Corrupt databases fail closed for recall without blocking the task.

Storage is local SQLite at `.owa/lessons.db`, namespaced by the canonical workspace
path. Copying that database to another workspace does not expose the old lessons.
Symlinked state directories or databases are rejected. These checks prevent
accidental sharing, not malicious filesystem races or same-user modification.
Relocated projects require explicit reproposal/review. No cloud calls or new
runtime dependencies are needed. Relevance ranking, expiry, reviewer models,
MCP memory tools, and model-based routing remain future work.
