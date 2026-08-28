from dotenv import load_dotenv

from app.service import AgentService


HELP_TEXT = """Commands:
  /help    Show this help
  /index   Rebuild the semantic project index
  /status  Show index status
  /clear   Clear conversation history
  /quit    Exit the agent
"""


def show_status(service):
    status = service.status()
    if not status["ready"]:
        print("Index: not found")
        return

    print(f"Index: ready ({status['chunks']} chunks)")


def main():

    load_dotenv()

    print()
    print("╭──────────────────────────────────────────────╮")
    print("│        LOCAL AMAZON Q — PHASE 1              │")
    print("│        Client Agent + Remote Ollama           │")
    print("╰──────────────────────────────────────────────╯")
    print()

    service = AgentService()

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
            show_status(service)
            continue

        if command == "/clear":
            service.clear()
            print("Conversation cleared.")
            continue

        if command == "/index":
            try:
                service.index()
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

            answer = service.chat(user_input)

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