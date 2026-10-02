"""Review memory outside the model tool surface: python -m app.memory."""
import argparse
import json
import sqlite3
from pathlib import Path

from app.memory.lessons import LessonStore


def main(argv=None):
    parser = argparse.ArgumentParser(description="Review OwA workspace lessons")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    propose = commands.add_parser("propose")
    propose.add_argument("content")
    propose.add_argument("--source", required=True)
    for name in ("approve", "reject", "revoke"):
        command = commands.add_parser(name)
        command.add_argument("id", type=int)
    args = parser.parse_args(argv)
    store = LessonStore(args.workspace)
    try:
        if args.command == "list":
            print(json.dumps(store.list(), ensure_ascii=True, indent=2))
        elif args.command == "propose":
            print(f"Pending lesson {store.propose(args.content, args.source)}")
        else:
            store.review(args.id, {"approve": "approved", "reject": "rejected", "revoke": "revoked"}[args.command])
            print(f"Lesson {args.id}: {args.command}")
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
