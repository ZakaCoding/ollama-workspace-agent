import ast
import json
import re

from app.tools.filesystem import resolve_path


SUPPORTED_EXTENSIONS = {".py"}
SECRET_PATTERN = re.compile(
    r"\b(password|passwd|secret|api[_-]?key|token)\b\s*"
    r"[:=]\s*['\"][^'\"]+['\"]",
    re.IGNORECASE,
)


def _issue(
    line: int,
    severity: str,
    category: str,
    message: str,
    evidence: str = "",
) -> dict:
    return {
        "line": line,
        "severity": severity,
        "category": category,
        "message": message,
        "evidence": evidence,
    }


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        parts = []
        current = node.func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def _scan_python(source: str) -> list[dict]:
    issues = []
    source_lines = source.splitlines()

    def evidence(line_number: int) -> str:
        return source_lines[line_number - 1].strip()

    for line_number, line in enumerate(source_lines, 1):
        if SECRET_PATTERN.search(line) and not re.search(
            r"(?:example|dummy|test|your[_-]?value)",
            line,
            re.IGNORECASE,
        ):
            issues.append(
                _issue(
                    line_number,
                    "high",
                    "hardcoded-secret",
                    "Possible hardcoded credential or token.",
                    evidence(line_number),
                )
            )

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return issues + [
            _issue(
                exc.lineno or 1,
                "info",
                "syntax-error",
                f"Python source could not be parsed: {exc.msg}",
                evidence(exc.lineno or 1),
            )
        ]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = _call_name(node)
        if name in {"eval", "exec"}:
            issues.append(
                _issue(
                    node.lineno,
                    "high",
                    "dynamic-execution",
                    f"{name}() executes dynamically supplied code.",
                    evidence(node.lineno),
                )
            )
        elif name == "os.system":
            issues.append(
                _issue(
                    node.lineno,
                    "high",
                    "shell-injection",
                    "os.system() executes a shell command; validate inputs and prefer argument lists.",
                    evidence(node.lineno),
                )
            )
        elif name in {"subprocess.run", "subprocess.Popen", "subprocess.call"}:
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    issues.append(
                        _issue(
                            node.lineno,
                            "high",
                            "shell-injection",
                            "subprocess is configured with shell=True.",
                            evidence(getattr(keyword, "lineno", node.lineno)),
                        )
                    )
        elif name == "hashlib.md5":
            issues.append(
                _issue(
                    node.lineno,
                    "medium",
                    "weak-cryptography",
                    "MD5 should not be used for passwords or security-sensitive hashes.",
                    evidence(node.lineno),
                )
            )

    return issues


def review_file(path: str) -> str:
    try:
        target = resolve_path(path)
    except (PermissionError, TypeError) as exc:
        return json.dumps({"path": path, "error": str(exc)})

    if target.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return json.dumps({
            "path": path,
            "issues": [],
            "message": "Only Python files are currently supported.",
        })

    if not target.exists():
        return json.dumps({"path": path, "error": "File does not exist."})
    if not target.is_file():
        return json.dumps({"path": path, "error": "Path is not a file."})

    try:
        source = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return json.dumps({"path": path, "error": str(exc)})

    issues = _scan_python(source)
    return json.dumps({
        "path": path,
        "issues": issues,
        "issue_count": len(issues),
        "vulnerable": bool(issues),
    })
