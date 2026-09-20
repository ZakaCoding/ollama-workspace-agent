"""Opt-in live Ollama evaluation in disposable workspaces.

Run: python scripts/eval-agent.py --model qwen2.5-coder:7b
No model downloads. Only each fixture's exact verification command is auto-approved.
"""

import argparse
from contextlib import redirect_stdout, redirect_stderr
from functools import partial
import io
import json
import os
from pathlib import Path
import sqlite3
import statistics
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CASES = (
    "greeting", "read", "retrieval", "edit", "learn", "legacy_search",
    "recovery", "multi_file", "long_history", "direct_list", "direct_read",
    "command", "polite_edit", "git_edit", "create", "review", "read_only", "git_read",
)
EDIT_CASES = {"edit", "recovery", "multi_file", "polite_edit", "git_edit"}
PROBE_COMMAND = 'python -c "print(6 * 7)"'


def snapshot(workspace):
    return {
        str(path.relative_to(workspace)): path.read_bytes()
        for path in workspace.rglob("*")
        if path.is_file()
        and not set(path.relative_to(workspace).parts) & {".owa", ".git", "__pycache__"}
    }


def summarize(results):
    timings = [row["seconds"] for row in results if "seconds" in row]
    return {
        "runs": len(results),
        "passed": sum(bool(row["passed"]) for row in results),
        "failed_cases": [row["case"] for row in results if not row["passed"]],
        "infrastructure_failures": sum(row.get("failure_kind") == "infrastructure" for row in results),
        "median_seconds": round(statistics.median(timings), 2) if timings else None,
        "total_agent_seconds": round(sum(timings), 2),
        "tool_calls": sum(len(row.get("tools", [])) for row in results),
        "model_requests": sum(row.get("metrics", {}).get("requests", 0) for row in results),
    }


def preflight(model):
    """Fail promptly when the server is unreachable or the model is absent."""
    from dotenv import load_dotenv
    import requests

    load_dotenv(ROOT / ".env")
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    response = requests.get(base_url + "/models", timeout=10)
    response.raise_for_status()
    installed = {entry["id"] for entry in response.json()["data"]}
    if model not in installed:
        raise ValueError(f"Requested model is not installed: {model}")


def run_case(model, case):
    sys.path.insert(0, str(ROOT))
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    os.environ["LLM_MODEL"] = model
    with TemporaryDirectory(prefix="owa-agent-eval-") as directory:
        os.chdir(directory)
        workspace = Path(directory)
        (workspace / "calculator.py").write_text("def add(a, b):\n    return a - b\n")
        (workspace / "test_calculator.py").write_text(
            "import unittest\nfrom calculator import add\n\n"
            "class AddTests(unittest.TestCase):\n"
            "    def test_add(self):\n"
            "        self.assertEqual(add(2, 3), 5)\n"
            "        self.assertEqual(add(-2, 3), 1)\n"
        )
        (workspace / "README.md").write_text(
            "Calculator demo. The add function is in calculator.py.\n"
            "Run tests with `python -m unittest -q`.\n"
        )
        if case == "multi_file":
            (workspace / "operations.py").write_text("def multiply(a, b):\n    return a + b\n")
            with (workspace / "test_calculator.py").open("a") as test:
                test.write("\n    def test_multiply(self):\n        from operations import multiply\n        self.assertEqual(multiply(2, 3), 6)\n")
        if case == "review":
            (workspace / "unsafe.py").write_text("def evaluate(user_input):\n    return eval(user_input)\n")
        if case in {"git_edit", "git_read"}:
            subprocess.run(["git", "init", "-q"], check=True, capture_output=True)
        if case == "git_read":
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            subprocess.run([
                "git", "-c", "user.name=OwA benchmark", "-c", "user.email=benchmark@example.invalid",
                "-c", "commit.gpgsign=false", "commit", "-qm", "Add calculator fixture",
            ], check=True, capture_output=True)
            with (workspace / "README.md").open("a") as readme:
                readme.write("Pending documentation update.\n")
        from app.agent import core
        from app.indexer.index import index_project

        core.AgentState = partial(core.AgentState, max_iterations=8, max_tool_calls=20)
        agent = core.Agent()
        calls = []
        replies = []
        original_chat = agent.llm.chat

        def trace_chat(*args, **kwargs):
            result = original_chat(*args, **kwargs)
            message = result["choices"][0]["message"]
            replies.append({key: message[key] for key in ("content", "tool_calls") if key in message})
            return result

        agent.llm.chat = trace_chat
        for name, function in list(core.FUNCTIONS.items()):
            def recorded(_name=name, _function=function, **kwargs):
                allowed_edits = ({"calculator.py", "operations.py"} if case == "multi_file"
                                 else {"notes.txt"} if case == "create"
                                 else {"calculator.py"} if case in EDIT_CASES else set())
                if _name in {"patch_file", "write_file"} and kwargs.get("path") not in allowed_edits:
                    result = "Tool blocked: evaluation only permits modifying the fixture source files."
                elif _name == "run_command":
                    permitted = PROBE_COMMAND if case == "command" else "python -m unittest -q"
                    if kwargs.get("command") != permitted:
                        result = "Command rejected by evaluation: only the fixture verification command is approved."
                    else:
                        with patch("app.tools.shell.Confirm.ask", return_value=True):
                            result = _function(**kwargs)
                else:
                    result = _function(**kwargs)
                calls.append({"name": _name, "arguments": kwargs, "result": result})
                return result
            core.FUNCTIONS[name] = recorded

        tasks = {
            "greeting": "hello",
            "read": "Read calculator.py using read_file and tell me what add currently returns.",
            "retrieval": "Where is the add function defined?",
            "edit": "Fix add in calculator.py so it adds two numbers instead of subtracting. Read it first, patch it, then run python -m unittest -q to verify. Do not modify the tests.",
            "learn": "learn this project",
            "legacy_search": "Use search_code to find the add function, then describe what it returns.",
            "recovery": "Run python -m unittest -q and fix any failure in calculator.py, then run python -m unittest -q again. Do not modify the tests.",
            "multi_file": "Fix add in calculator.py and multiply in operations.py and run python -m unittest -q to verify both fixes. Do not modify the tests.",
            "long_history": "learn this project",
            "direct_list": "List the files in the current directory using list_dir.",
            "direct_read": "Show calculator.py using read_file and explain what add returns.",
            "command": f"Run {PROBE_COMMAND} and tell me its output.",
            "polite_edit": "can u fix calculator.py so add adds instead of subtracts, then run python -m unittest -q. Do not modify tests.",
            "git_edit": "Check git status and fix calculator.py so add adds instead of subtracts, then run python -m unittest -q. Do not modify tests.",
            "create": "Create notes.txt containing exactly 'Calculator notes' and read it back to verify.",
            "review": "Review unsafe.py using code_review for security risks. Do not edit it.",
            "read_only": "Read calculator.py and explain the bug. Do not fix it or run commands.",
            "git_read": "Use git_status, then use git_diff and use git_log. Report the pending change and latest commit. Do not edit files.",
        }
        if case == "greeting":
            agent.messages += [
                {"role": "user", "content": "Read all markdown files"},
                {"role": "assistant", "content": "python3 - <<'PY'\nimport os\nprint(os.listdir('.'))\nPY"},
            ]
        if case == "retrieval":
            index_project(workspace, workspace / ".owa" / "index.db")
        if case in {"learn", "legacy_search"}:
            # Reproduce the pre-FTS schema found in the user's real workspace.
            (workspace / ".owa").mkdir(exist_ok=True)
            with sqlite3.connect(workspace / ".owa" / "index.db") as db:
                db.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, path TEXT, chunk_index INTEGER, content TEXT, embedding BLOB)")
                db.execute("INSERT INTO documents VALUES (1, 'calculator.py', 0, ?, '[1,0]')",
                           ((workspace / "calculator.py").read_text(),))
        if case == "long_history":
            for _ in range(25):
                agent.messages += [
                    {"role": "user", "content": "Describe the old weather app"},
                    {"role": "assistant", "content": "The weather app uses Redis and Kubernetes. " * 20},
                ]
        # Capture after fixture setup: indexing may create .gitignore itself.
        original_files = snapshot(workspace)
        started = perf_counter()
        answer = "".join(agent.stream(tasks[case]))
        elapsed = round(perf_counter() - started, 2)
        if case == "greeting":
            passed = bool(answer.strip()) and len(answer) < 300 and not calls and any(
                word in answer.lower() for word in ("hello", "hi", "hey")
            ) and not any(word in answer for word in ("```", "python", "os.listdir"))
        elif case in {"read", "legacy_search", "direct_read", "read_only"}:
            tool = "search_code" if case == "legacy_search" else "read_file"
            passed = any(c["name"] == tool and "def add" in c["result"] for c in calls)
            passed = passed and any(term in answer.lower() for term in ("subtract", "difference", "a - b"))
        elif case == "retrieval":
            passed = "[calculator.py#chunk=0]" in answer and not calls
        elif case in {"learn", "long_history"}:
            passed = "calculator" in answer.lower() and "[README.md#chunk=0]" in answer
            passed = passed and not calls and not any(word in answer.lower() for word in ("redis", "kubernetes"))
        elif case == "direct_list":
            passed = any(c["name"] == "list_dir" and "calculator.py" in c["result"] for c in calls)
            passed = passed and all(name in answer for name in original_files)
        elif case == "command":
            passed = any(c["name"] == "run_command" and "STDOUT:\n42" in c["result"]
                         and "EXIT_CODE=0" in c["result"] for c in calls) and "42" in answer
        elif case == "create":
            passed = (workspace / "notes.txt").is_file() and (workspace / "notes.txt").read_text() == "Calculator notes"
            passed = passed and any(c["name"] == "read_file" and c["arguments"].get("path") == "notes.txt" for c in calls)
        elif case == "review":
            passed = any(c["name"] == "code_review" and c["arguments"].get("path") == "unsafe.py" for c in calls)
            passed = passed and "eval" in answer.lower()
        elif case == "git_read":
            passed = {c["name"] for c in calls} >= {"git_status", "git_diff", "git_log"}
            passed = passed and "README.md" in answer and "calculator fixture" in answer.lower()
        else:
            check = subprocess.run([sys.executable, "-m", "unittest", "-q"], capture_output=True, text=True, timeout=10)
            passed = check.returncode == 0 and any(c["name"] == "patch_file" for c in calls)
            passed = passed and any(c["name"] == "run_command" and "EXIT_CODE=0" in c["result"] for c in calls)
            if case == "recovery":
                command_results = [c["result"] for c in calls if c["name"] == "run_command"]
                passed = passed and len(command_results) >= 2 and "EXIT_CODE=1" in command_results[0]
            if case == "multi_file":
                patched = {c["arguments"]["path"] for c in calls if c["name"] == "patch_file"}
                passed = passed and patched == {"calculator.py", "operations.py"}
            if case == "git_edit":
                passed = passed and any(c["name"] == "git_status" for c in calls)
        allowed_changes = ({"calculator.py", "operations.py"} if case == "multi_file"
                           else {"calculator.py"} if case in EDIT_CASES
                           else {"notes.txt"} if case == "create" else set())
        final_files = snapshot(workspace)
        files_preserved = all(
            original_files.get(name) == final_files.get(name)
            for name in original_files.keys() | final_files.keys() if name not in allowed_changes
        )
        passed = passed and files_preserved
        if case == "read_only":
            passed = passed and all(c["name"] not in {"write_file", "patch_file", "run_command"} for c in calls)
        passed = passed and agent.state.completed
        metrics = agent.llm.metrics.snapshot()
        return {"case": case, "model": model, "passed": bool(passed), "seconds": elapsed,
                "answer": answer, "tools": calls, "errors": agent.state.errors,
                "files_preserved": files_preserved,
                "completed": agent.state.completed,
                "failure_kind": (None if passed else "infrastructure"
                                 if metrics["requests"] and metrics["failed_requests"] == metrics["requests"]
                                 else "agent"),
                "replies": replies, "metrics": metrics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--cases", choices=CASES, nargs="+", help="Run a selected subset")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    if args.case:
        captured = io.StringIO()
        with redirect_stdout(captured), redirect_stderr(captured):
            result = run_case(args.model, args.case)
        print(json.dumps(result))
        return
    try:
        preflight(args.model)
    except Exception as exc:
        print(json.dumps({"error": "Ollama preflight failed", "kind": type(exc).__name__,
                          "detail": "Check server connectivity and the installed model name."}), flush=True)
        sys.exit(2)
    results = []
    for run, case in ((run, case) for run in range(1, args.repeat + 1) for case in (args.cases or CASES)):
        try:
            child = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--model", args.model, "--case", case],
                capture_output=True, text=True, timeout=240,
            )
            result = json.loads(child.stdout) if child.returncode == 0 else {
                "case": case, "passed": False, "error": child.stderr[-2000:],
            }
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            result = {"case": case, "passed": False, "error": str(exc)}
        result["run"] = run
        results.append(result)
        print(json.dumps({key: result[key] for key in ("case", "run", "passed", "seconds", "error") if key in result}), flush=True)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(results, indent=2) + "\n")
        if result.get("failure_kind") == "infrastructure":
            break
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"summary": summarize(results),
                      "planned_runs": len(args.cases or CASES) * args.repeat}), flush=True)
    sys.exit(0 if all(r["passed"] for r in results) else 1)


if __name__ == "__main__":
    main()
