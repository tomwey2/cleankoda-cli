import argparse
import sys

from cleankoda_cli.agent import SYSTEM_PROMPT, run_agent
from cleankoda_cli.commands import CommandContext, registry
from cleankoda_cli.memory import Memory
from cleankoda_cli.tui import run_tui


def run_headless(prompt_text: str, mem: Memory) -> None:
    """Führt den Prompt im Headless-Modus (ohne TUI) aus."""
    # Slash-Command Check
    if prompt_text.startswith("/"):
        ctx = CommandContext(memory=mem)
        result = registry.dispatch(prompt_text, ctx)
        if result.output:
            print(result.output)
        return

    mem.add_user(prompt_text)
    response = run_agent(mem)
    if response:
        print(response)


def main(argv: list[str] | None = None) -> None:
    memory = Memory(system_prompt=SYSTEM_PROMPT, file=".agents/memory.json")

    parser = argparse.ArgumentParser(description="cleankoda CLI")
    parser.add_argument("prompt_pos", nargs="*", help="Optionaler Prompt (Headless)")
    parser.add_argument("-p", "--prompt", help="Prompt für den Headless-Modus")
    parser.add_argument("--headless", action="store_true", help="Erzwingt Headless-Modus")
    parser.add_argument("--tui", action="store_true", help="Erzwingt TUI-Modus")

    args = parser.parse_args(argv)
    prompt_parts = args.prompt_pos if args.prompt_pos else []
    pos_prompt = " ".join(prompt_parts).strip() if prompt_parts else None
    prompt = args.prompt or pos_prompt

    piped_input = None
    if not sys.stdin.isatty():
        try:
            piped_input = sys.stdin.read().strip()
        except OSError:
            piped_input = None

    final_prompt = prompt or piped_input

    if args.tui:
        run_tui(memory)
    elif args.headless or final_prompt is not None:
        if not final_prompt:
            print("Error: Headless mode requires a prompt argument or piped standard input.", file=sys.stderr)
            sys.exit(1)
        run_headless(final_prompt, memory)
    else:
        run_tui(memory)


if __name__ == "__main__":
    main()
