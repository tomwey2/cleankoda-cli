import argparse
import asyncio
import sys

from cleankoda.agent import SYSTEM_PROMPT, run_agent
from cleankoda.commands import CommandContext, registry
from cleankoda.memory import Memory
from cleankoda.session_state import SessionState
from cleankoda.tools import sandbox_manager
from cleankoda.tui import run_tui


def headless_status_callback(status: str | None) -> None:
    if status:
        print(f"▶ {status}", file=sys.stderr)


async def _run_headless_async(prompt_text: str, memory: Memory, cancel_event: asyncio.Event) -> int:
    memory.add_user(prompt_text)
    state = SessionState.load()
    try:
        async for chunk in run_agent(
            memory=memory,
            state=state,
            status_callback=headless_status_callback,
            cancel_event=cancel_event,
        ):
            print(chunk, end="", flush=True)
        print()
        return 0
    except Exception as e:
        print(f"Error running agent: {e}", file=sys.stderr)
        return 1


def run_headless(prompt_text: str, memory: Memory) -> int:
    """Execute the prompt in headless mode without TUI.

    Returns exit code 0 on success, or 1 on failure.
    """
    try:
        # Slash-Command Check
        if prompt_text.startswith("/"):
            ctx = CommandContext(memory=memory)
            result = registry.dispatch(prompt_text, ctx)
            if result.output:
                print(result.output)
            return 0

        cancel_event = asyncio.Event()
        return asyncio.run(_run_headless_async(prompt_text, memory, cancel_event))
    finally:
        sandbox_manager.stop()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="cleankoda CLI")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--tui", action="store_true", help="Force TUI mode")
    mode_group.add_argument("--headless", action="store_true", help="Force headless mode")
    parser.add_argument("prompt_pos", nargs="*", help="Optionaler Prompt (Headless)")
    parser.add_argument("-p", "--prompt", help="Prompt für den Headless-Modus")

    args = parser.parse_args(argv)

    prompt_parts = args.prompt_pos if args.prompt_pos else []
    pos_prompt = " ".join(prompt_parts).strip() if prompt_parts else None
    prompt = args.prompt or pos_prompt

    piped_input = None
    if not sys.stdin.isatty():
        try:
            piped_input = sys.stdin.read().strip()
        except OSError as err:
            print(f"Warning: Could not read standard input: {err}", file=sys.stderr)

    if prompt and piped_input:
        final_prompt = f"{prompt}\n\n{piped_input}"
    else:
        final_prompt = prompt or piped_input

    memory = Memory(system_prompt=SYSTEM_PROMPT, file=".agents/memory.json")

    if args.tui:
        run_tui(memory)
    elif args.headless or final_prompt is not None:
        if not final_prompt:
            print("Error: Headless mode requires a prompt argument or piped standard input.", file=sys.stderr)
            sys.exit(1)
        code = run_headless(final_prompt, memory)
        if isinstance(code, int) and code != 0:
            sys.exit(code)
    else:
        run_tui(memory)


if __name__ == "__main__":
    main()
