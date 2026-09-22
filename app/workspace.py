"""Per-service workspace binding, including background tool execution."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

_active_workspace: ContextVar[Path | None] = ContextVar('owa_workspace', default=None)


def current_workspace(default: Path | None = None) -> Path:
    return _active_workspace.get() or default or Path.cwd().resolve()


def history_path(default: Path) -> Path:
    active = _active_workspace.get()
    return active / '.owa' / 'history.json' if active is not None else default


@contextmanager
def workspace_scope(path: Path):
    token = _active_workspace.set(path.resolve())
    try:
        yield
    finally:
        _active_workspace.reset(token)
