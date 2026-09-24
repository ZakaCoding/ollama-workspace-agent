"""Fail-closed approval for agent-initiated changes."""

import os

from rich.console import Console
from rich.prompt import Confirm

console = Console(stderr=True)


def approve(action: str, detail: str, *, variable: str = "OWA_WRITE_APPROVAL") -> bool:
    policy = os.getenv(variable, "ask").lower()
    if policy == "deny":
        return False
    if policy == "allow":
        return True
    if policy != "ask":
        return False
    console.print(f"[bold yellow]OwA requests {action}:[/bold yellow] {detail}")
    try:
        return Confirm.ask("Allow?", default=False)
    except (EOFError, KeyboardInterrupt):
        return False
