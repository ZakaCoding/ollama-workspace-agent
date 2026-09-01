import argparse
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv, set_key
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status
from rich.theme import Theme

from app.config import ENV_PATH, ensure_config_dir
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
  [cmd]/model[/cmd]   switch chat model
  [cmd]/clear[/cmd]   clear conversation
  [cmd]/setup[/cmd]   configure Ollama connection
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


def run_model():
    load_dotenv(ENV_PATH, override=True)
    load_dotenv(Path.cwd() / ".env", override=True)
    base_url = os.getenv("LLM_BASE_URL", "").replace("/v1", "").rstrip("/")
    current = os.getenv("LLM_MODEL", "")
    models = []

    if base_url:
        try:
            resp = httpx.get(f"{base_url}/api/tags", timeout=5)
            models = [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass

    if models:
        console.print("\n[cmd]Available models:[/cmd]")
        for i, m in enumerate(models, 1):
            marker = " [muted](current)[/muted]" if m == current else ""
            console.print(f"  [muted]{i}.[/muted] {m}{marker}")
        console.print()

    model = Prompt.ask("[prompt]Chat model[/prompt]", default=current)
    if not model or model == current:
        console.print("[muted]No change.[/muted]")
        return

    ensure_config_dir()
    if not ENV_PATH.exists():
        ENV_PATH.write_text("")
    set_key(ENV_PATH, "LLM_MODEL", model)
    os.environ["LLM_MODEL"] = model
    console.print(f"[muted]Model set to {model}. Restart owa for changes to take effect.[/muted]\n")


def run_setup():
    console.print()
    console.print("[cmd]OwA Setup[/cmd] — configure your Ollama connection")
    console.print(f"[muted]Config will be saved to {ENV_PATH}[/muted]\n")

    ensure_config_dir()

    llm_url = Prompt.ask(
        "[prompt]Ollama host URL[/prompt]",
        default=os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
    )
    llm_model = Prompt.ask(
        "[prompt]Chat model[/prompt]",
        default=os.getenv("LLM_MODEL", "llama3.1:8b"),
    )
    embed_url = Prompt.ask(
        "[prompt]Embedding host URL[/prompt]",
        default=os.getenv("EMBEDDING_BASE_URL", "http://127.0.0.1:11434"),
    )
    embed_model = Prompt.ask(
        "[prompt]Embedding model[/prompt]",
        default=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
    )
    api_key = Prompt.ask(
        "[prompt]API key (leave blank to skip)[/prompt]",
        default=os.getenv("API_KEY", ""),
        password=True,
    )

    if not ENV_PATH.exists():
        ENV_PATH.write_text("")

    set_key(ENV_PATH, "LLM_BASE_URL", llm_url)
    set_key(ENV_PATH, "LLM_MODEL", llm_model)
    set_key(ENV_PATH, "EMBEDDING_BASE_URL", embed_url)
    set_key(ENV_PATH, "EMBEDDING_MODEL", embed_model)
    if api_key:
        set_key(ENV_PATH, "API_KEY", api_key)

    console.print(f"\n[muted]Saved to {ENV_PATH}[/muted]")
    console.print("[muted]Restart owa for changes to take effect.[/muted]\n")


def _inject_file_context(message: str) -> str:
    import re
    matches = re.findall(r"@(\S+)", message)
    if not matches:
        return message
    injected = []
    for ref in matches:
        path = Path.cwd() / ref
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                injected.append(f"--- @{ref} ---\n{content}\n--- end ---")
                message = message.replace(f"@{ref}", ref)
            except Exception:
                pass
    if injected:
        message = "\n\n".join(injected) + "\n\n" + message
    return message


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="OwA · Ollama Workspace Agent")
    parser.add_argument("--api-url", help="Use the FastAPI server instead of direct mode.")
    parser.add_argument("--api-key", default=os.getenv("API_KEY"), help="API key for the FastAPI server.")
    return parser.parse_args(argv)


def main(argv=None):
    load_dotenv(ENV_PATH)
    load_dotenv(Path.cwd() / ".env", override=True)

    args = parse_args(argv)

    mode = "api client" if args.api_url else "direct"
    print_banner(mode)

    if not os.getenv("LLM_BASE_URL"):
        console.print("[error]No config found.[/error] [muted]Run /setup to configure OwA.[/muted]\n")

    service = (
        ApiClient(args.api_url, args.api_key)
        if args.api_url
        else AgentService()
    )

    if not args.api_url:
        status = service.status()
        if not status["ready"]:
            console.print("[muted]No index found — indexing workspace…[/muted]")
            try:
                with Status("[muted]indexing…[/muted]", console=console, spinner="dots"):
                    service.index()
                console.print("[muted]Index ready.[/muted]\n")
            except Exception as exc:
                console.print(f"[error]auto-index failed:[/error] {exc}\n")

    while True:
        try:
            user_input = Prompt.ask("\n[prompt]›[/prompt]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[muted]Bye.[/muted]")
            break

        if not user_input:
            continue

        command = user_input.lower()

        if command == "/model":
            run_model()
            continue

        if command == "/setup":
            run_setup()
            continue

        if command == "/help":
            console.print(HELP_TEXT)
            continue

        if command == "/status":
            try:
                status = service.status()
                model = os.getenv("LLM_MODEL", "unknown")
                if status["ready"]:
                    console.print(f"[muted]index ready · {status['chunks']} chunks · model {model}[/muted]")
                else:
                    console.print(f"[muted]index not found · model {model}[/muted]")
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
            chunks = []
            message = _inject_file_context(user_input)
            with Status("[muted]thinking…[/muted]", console=console, spinner="dots"):
                for chunk in service.chat_stream(message):
                    chunks.append(chunk)
            console.print(Markdown("".join(chunks)))
        except Exception as exc:
            console.print(f"\n[error]agent error:[/error] {exc}\n")


if __name__ == "__main__":
    main()
