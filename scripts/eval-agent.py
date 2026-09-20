"""Opt-in live Ollama evaluation in disposable workspaces.

Run: python scripts/eval-agent.py --model qwen2.5-coder:7b
No model downloads. Only the fixture's exact unittest command is auto-approved.
"""

import argparse
from contextlib import redirect_stdout, redirect_stderr
from functools import partial
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CASES = ("greeting", "read", "retrieval", "edit")


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
        (workspace / "README.md").write_text("Calculator demo. The add function is in calculator.py.\n")
        original_files = {p.name: p.read_text() for p in workspace.iterdir() if p.is_file()}
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
                if _name in {"patch_file", "write_file"} and kwargs.get("path") != "calculator.py":
                    result = "Tool blocked: evaluation only permits modifying calculator.py."
                elif _name == "run_command":
                    if kwargs.get("command") != "python -m unittest -q":
                        result = "Command rejected by evaluation: only python -m unittest -q is approved."
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
        }
        if case == "greeting":
            agent.messages += [
                {"role": "user", "content": "Read all markdown files"},
                {"role": "assistant", "content": "python3 - <<'PY'\nimport os\nprint(os.listdir('.'))\nPY"},
            ]
        if case == "retrieval":
            index_project(workspace, workspace / ".owa" / "index.db")
        started = perf_counter()
        answer = "".join(agent.stream(tasks[case]))
        elapsed = round(perf_counter() - started, 2)
        if case == "greeting":
            passed = bool(answer.strip()) and len(answer) < 300 and not calls and any(
                word in answer.lower() for word in ("hello", "hi", "hey")
            ) and not any(word in answer for word in ("```", "python", "os.listdir"))
        elif case == "read":
            passed = any(c["name"] == "read_file" and c["arguments"].get("path") == "calculator.py" for c in calls)
            passed = passed and any(term in answer.lower() for term in ("subtract", "difference", "a - b"))
        elif case == "retrieval":
            passed = "[calculator.py#chunk=0]" in answer and not calls
        else:
            check = subprocess.run([sys.executable, "-m", "unittest", "-q"], capture_output=True, text=True, timeout=10)
            passed = check.returncode == 0 and any(c["name"] == "patch_file" for c in calls)
            passed = passed and any(c["name"] == "run_command" and "EXIT_CODE=0" in c["result"] for c in calls)
        passed = passed and all(
            (workspace / name).read_text() == content
            for name, content in original_files.items()
            if case != "edit" or name != "calculator.py"
        )
        passed = passed and agent.state.completed
        return {"case": case, "model": model, "passed": bool(passed), "seconds": elapsed,
                "answer": answer, "tools": calls, "errors": agent.state.errors,
                "replies": replies, "metrics": agent.llm.metrics.snapshot()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.case:
        captured = io.StringIO()
        with redirect_stdout(captured), redirect_stderr(captured):
            result = run_case(args.model, args.case)
        print(json.dumps(result))
        return
    results = []
    for case in CASES:
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
        results.append(result)
        print(json.dumps(result), flush=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2) + "\n")
    sys.exit(0 if all(r["passed"] for r in results) else 1)


if __name__ == "__main__":
    main()
