# Python Environment & Code Standards

### Package Management & Verification
- Exclusively use `uv` for package management, running scripts, and testing (`uv add <pkg>`, `uv run pytest`, `uv run python src/main.py`).
- Run code checks via CLI inline commands only: `uv run python -c '...'` from the project root. Never create temporary scratchpad scripts.
- **Static Analysis:** Always run `pyrefly check src` to verify changes. Code must pass without type or lint errors before finishing a task.

### Code Style
- **Imports:** Place all imports strictly at the top of the file. Group standard library, third-party, and internal packages cleanly (PEP 8). No inline or late imports inside functions/methods.
- **Type Annotations:** Strictly use modern Python type hinting (`list[str]`, `dict[str, Any]`, `X | None`).

### Language Policy
- **English Only:** All code, comments, docstrings, log messages, and UI text (status lines, prompts, dialogs, error messages) MUST be written in English.
- The German conversational prompt with the user does NOT apply to generated code or user interfaces.
