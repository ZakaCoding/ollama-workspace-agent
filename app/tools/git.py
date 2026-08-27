import subprocess

from app.tools.filesystem import WORKSPACE


def git_status() -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--branch"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        return (
            "Not a git repository.\n"
            + result.stderr.strip()
        )

    return result.stdout.strip()


def git_diff() -> str:
    result = subprocess.run(
        ["git", "diff"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=30,
    )

    return result.stdout.strip()


def git_log() -> str:
    result = subprocess.run(
        [
            "git",
            "log",
            "--oneline",
            "-20",
        ],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        return result.stderr.strip()

    return result.stdout.strip()