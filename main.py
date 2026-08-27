from dotenv import load_dotenv

from app.agent import Agent


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

        if user_input.lower() in {
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