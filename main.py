import argparse
import os

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status
from rich.theme import Theme

from app.api_client import ApiClient
from app.service import AgentService

THEME = Theme({
    "prompt":    "bold cyan",
    "assistant": "bold green",
    "cmd":       "bold yellow",
    "error":     "bold red",
    "muted":     "dim white",
})

console = Console(theme=THEME)

HELP_TEXT = """[cmd]Commands[/cmd]
  [cmd]/index[/cmd]   rebuild project index
  [cmd]/status[/cmd]  show index status
  [cmd]/clear[/cmd]   clear conversation
  [cmd]/quit[/cmd]    exit"""


def print_banner(mode: str):
    console.print(Panel(
        "[bold cyan]OwA[/bold cyan] · Ollama Workspace Agent\n"
        "[muted]An open-source local coding assistant powered by Ollama.\n"
        "Runs entirely on your own hardware.[/muted]",
        subtitle=f"[muted]{mode} · /help for commands[/muted]",
        border_style="cyan",
        expand=False,
        width=62,
    ))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="OwA · Ollama Workspace Agent")
    parser.add_argument("--api-url", help="Use the FastAPI server instead of direct mode.")
    parser.add_argument("--api-key", default=os.getenv("API_KEY"), help="API key for the FastAPI server.")
    return parser.parse_args(argv)


def main(argv=None):
    load_dotenv()
    args = parse_args(argv)

    mode = "api client" if args.api_url else "direct"
    print_banner(mode)

    service = (
        ApiClient(args.api_url, args.api_key)
        if args.api_url
        else AgentService()
    )

    while True:
        try:
            user_input = Prompt.ask("\n[prompt]›[/prompt]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[muted]Bye.[/muted]")
            break

        if not user_input:
            continue

        command = user_input.lower()

        if command == "/help":
            console.print(HELP_TEXT)
            continue

        if command == "/status":
            try:
                status = service.status()
                if status["ready"]:
                    console.print(f"[muted]index ready · {status['chunks']} chunks[/muted]")
                else:
                    console.print("[muted]index not found[/muted]")
            except Exception as exc:
                console.print(f"[error]status error:[/error] {exc}")
            continue

        if command == "/clear":
            try:
                service.clear()
                console.print("[muted]conversation cleared[/muted]")
            except Exception as exc:
                console.print(f"[error]clear error:[/error] {exc}")
            continue

        if command == "/index":
            try:
                with Status("[muted]indexing…[/muted]", console=console, spinner="dots"):
                    result = service.index()
                msg = result.get("status", "complete") if isinstance(result, dict) else "complete"
                console.print(f"[muted]index {msg}[/muted]")
            except Exception as exc:
                console.print(f"[error]index error:[/error] {exc}")
            continue

        if command in {"exit", "quit", "/exit", "/quit"}:
            console.print("[muted]Bye.[/muted]")
            break

        try:
            console.print()
            console.print("[assistant]assistant[/assistant]")
            if args.api_url:
                response_text = ""
                for chunk in service.chat_stream(user_input):
                    print(chunk, end="", flush=True)
                    response_text += chunk
                print()
            else:
                with Status("[muted]thinking…[/muted]", console=console, spinner="dots"):
                    response = service.chat(user_input)
                console.print(Markdown(response))
        except Exception as exc:
            console.print(f"\n[error]agent error:[/error] {exc}\n")


if __name__ == "__main__":
    main()
