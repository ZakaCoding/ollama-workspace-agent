import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from app.agent import Agent
from app.agent.core import WORKSPACE
from app.indexer.index import index_project


HELP_TEXT = """Commands:
  /help    Show this help
  /index   Rebuild the semantic project index
  /status  Show index status
  /clear   Clear conversation history
  /quit    Exit the agent
"""


def show_status():
    index_path = WORKSPACE / ".ai" / "index.db"
    if not index_path.exists():
        print("Index: not found")
        return

    with sqlite3.connect(index_path) as db:
        count = db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    print(f"Index: ready ({count} chunks)")


def main():

    load_dotenv()

    print()
    print("╭──────────────────────────────────────────────╮")
    print("│        LOCAL AMAZON Q — PHASE 1              │")
    print("│        Client Agent + Remote Ollama           │")
    print("╰──────────────────────────────────────────────╯")
    print()

    agent = Agent()

    while True:

        try:
            user_input = input("You › ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nBye.")
            break

        if not user_input:
            continue

        command = user_input.lower()

        if command == "/help":
            print(HELP_TEXT)
            continue

        if command == "/status":
            show_status()
            continue

        if command == "/clear":
            agent.clear()
            print("Conversation cleared.")
            continue

        if command == "/index":
            try:
                index_project(WORKSPACE, WORKSPACE / ".ai" / "index.db")
            except Exception as exc:
                print(f"Index error: {exc}")
            continue

        if command in {
            "exit",
            "quit",
            "/exit",
            "/quit",
        }:
            print("Bye.")
            break

        try:

            answer = agent.run(user_input)

            print()
            print("Agent ›")
            print(answer)
            print()

        except Exception as exc:

            print()
            print("❌ Agent error:")
            print(exc)
            print()


if __name__ == "__main__":
    main()