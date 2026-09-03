# Python package and project manager

Whenever you need to execute CLI commands for Python package management, running tests, or starting the application, you MUST strictly use `uv`.

**Execution Examples:**
- `uv add dotenv`
- `uv run pytest`
- `uv run python src/main.py`

If you want to verify or import code, DO NOT create scripts in your internal scratchpad. Always switch to the project's main directory and use only `uv run python -c '...'` to get the correct virtual environment context and Python path.
