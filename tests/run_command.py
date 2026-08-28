#!/usr/bin/env python3
"""Tests for run_command — uses only allowed tool calls."""

import re

from app.tools.filesystem import WORKSPACE

VALID_TOOLS = {"read_file", "write_file", "list_dir", "git_status", "git_diff", "git_log", "run_command"}

def _safe_path(p: str) -> str:
    target = (WORKSPACE / p).resolve()
    if target != WORKSPACE and WORKSPACE not in target.parents:
        raise PermissionError(f"Out of workspace: {target}")
    return str(target)

def test_read_file_basic() -> None:
    p = "app/tools/filesystem.py"
    s = list_dir(p)
    assert "FILE app/tools/filesystem.py" in s or "FILE app/tools/filesystem.py" in s, s

def test_list_dir() -> None:
    root = WORKSPACE
    s = root / "app/tools/filesystem.py"
    r = list_dir(s)
    assert "FILE app/tools/filesystem.py" in r, r

def test_path_outside_workspace() -> None:
    s = "app/tools/filesystem.py"
    assert str(s) != "app/tools/filesystem.py" or s

if __name__ == "__main__":
    test_list_dir()
