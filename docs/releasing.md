# Release validation

The 0.7.0 candidate covers context compression, service lifecycle and progress,
diagnostics, reproducible evaluation, MCP stdio tools, approval gates, a Docker
command sandbox, optional delegation, and local episodic memory. A versioned
local build is not a published release.

Create a clean virtual environment with Python 3.11–3.14, then run:

```bash
python -m pip install -r requirements-ci.txt
python -m pip install --no-build-isolation --no-deps -e '.[dev]'
python -m pip check
python -m pytest -q
python scripts/check-stream.py
python scripts/check-release.py v0.7.0
python -m build --no-isolation
```

`requirements-ci.txt` pins the test/build environment, including transitive
packages; normal installations retain the dependency ranges in `pyproject.toml`.
Update pins together, verify `pip check`, and run the Python matrix. The CI matrix
builds a wheel and source distribution after tests on each supported minor.

Before tagging, run the live evaluator against installed models, save the raw
traces under `benchmarks/`, and record model identifiers, budgets, test counts,
failures, and limits. Two rounds of the current suite produce 46 runs per model:

```bash
python scripts/eval-agent.py --model MODEL --repeat 2 --output .owa/eval.json
```

Before tagging, move the relevant `[Unreleased]` changes into the dated 0.7.0
entry in `CHANGELOG.md`, using the actual release date. Check an isolated
`pipx install .` and `owa --help`; MCP users also need the `[mcp]` extra.

To reproduce conversational drift with an existing history without modifying it:

```bash
python scripts/eval-agent.py --model MODEL --cases assistant_status large_tool_context --repeat 2 --history-fixture .owa/history.json --output .owa/response-regression.json
```

The history fixture is loaded only for `assistant_status` in a disposable
workspace. Traces record its hash, not its contents. Keep private histories out
of committed fixtures.

Groundedness is a set of fixture assertions (correct citation/location or
refusal), not semantic proof for arbitrary answers. Patch correctness uses
independent fixture tests. Tool success counts verified tool outcomes; an
expected initial failing test in a recovery case counts as a failed tool even
when the overall task succeeds. Timing excludes process startup and fixture
indexing; maximum and median latency are reported separately. Heartbeats and
tool event order are preserved in each trace.

After reviewing results, a maintainer can commit the milestone and push its
matching `vVERSION` tag. The publish workflow checks the version and dated
changelog, runs tests, builds distributions, uploads to PyPI, and creates a
GitHub release. Pushing that tag is the publication action; local validation
never performs it.
