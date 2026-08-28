import json

from app.agent.core import Agent
from app.tools.code_review import review_file
from app.tools.registry import FUNCTIONS, TOOLS


def test_code_review_reports_python_security_findings(tmp_path, monkeypatch):
    source = tmp_path / "sample.py"
    source.write_text(
        "import hashlib\n"
        "password = 'real-secret'\n"
        "value = eval(user_input)\n"
        "hashlib.md5(value)\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "app.tools.code_review.resolve_path",
        lambda _path: source,
    )
    result = json.loads(review_file("sample.py"))
    categories = {issue["category"] for issue in result["issues"]}

    assert result["vulnerable"]
    assert {"hardcoded-secret", "dynamic-execution", "weak-cryptography"} <= categories
    assert all(issue["line"] > 0 for issue in result["issues"])
    assert any("eval(user_input)" in issue["evidence"] for issue in result["issues"])


def test_code_review_rejects_paths_outside_workspace():
    result = json.loads(review_file("../outside.py"))

    assert "error" in result


def test_code_review_is_registered():
    names = {
        tool["function"]["name"]
        for tool in TOOLS
    }

    assert "code_review" in names
    assert FUNCTIONS["code_review"] is review_file


def test_agent_marks_unverified_completion_claims():
    agent = Agent()

    result = agent._add_verification_note("I created app/new.py")

    assert "not verified" in result


def test_agent_accepts_completion_claims_with_matching_evidence():
    agent = Agent()
    agent.state = type("State", (), {"files_changed": ["app/new.py"]})()

    result = agent._add_verification_note("I created app/new.py")

    assert "not verified" not in result
