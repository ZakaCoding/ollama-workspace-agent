import argparse
import os

from dotenv import load_dotenv

from app.api_client import ApiClient
from app.service import AgentService


HELP_TEXT = """Commands:
    /help    commands
    /index   rebuild project index
    /status  show index status
    /clear   clear conversation
    /quit    exit
"""


def show_status(service):
    status = service.status()
    if not status["ready"]:
        print("Index: not found")
        return

    print(f"Index: ready ({status['chunks']} chunks)")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Local coding agent CLI",
    )
    parser.add_argument(
        "--api-url",
        help="Use the FastAPI server instead of direct mode.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("API_KEY"),
        help="API key for the FastAPI server.",
    )
    return parser.parse_args(argv)


def main(argv=None):

    load_dotenv()
    args = parse_args(argv)

    mode = "API client" if args.api_url else "Direct service"
    print(f"local-agent | {mode} | /help for commands")

    service = (
        ApiClient(args.api_url, args.api_key)
        if args.api_url
        else AgentService()
    )

    while True:

        try:
            user_input = input("› ").strip()

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
            try:
                if args.api_url:
                    status = service.status()
                    if status["ready"]:
                        print(f"index ready | {status['chunks']} chunks")
                    else:
                        print("index not found")
                else:
                    show_status(service)
            except Exception as exc:
                print(f"status error: {exc}")
            continue

        if command == "/clear":
            try:
                service.clear()
                print("conversation cleared")
            except Exception as exc:
                print(f"clear error: {exc}")
            continue

        if command == "/index":
            try:
                result = service.index()
                if args.api_url:
                    print(f"index {result['status']}")
                else:
                    print("index complete")
            except Exception as exc:
                print(f"index error: {exc}")
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
            print("assistant:")
            if args.api_url:
                for chunk in service.chat_stream(user_input):
                    print(chunk, end="", flush=True)
                print()
            else:
                print(service.chat(user_input))
            print()

        except Exception as exc:

            print()
            print("❌ Agent error:")
            print(exc)
            print()


if __name__ == "__main__":
    main()