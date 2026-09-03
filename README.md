# cleankoda-cli

`cleankoda-cli` is a terminal-based AI coding agent for clean code software development built with Python, [Prompt Toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit), [Rich](https://github.com/Textualize/rich), and the [Mistral AI API](https://github.com/mistralai/client-python). It features a full TUI (Terminal User Interface) and interactive tool execution capabilities such as listing files, reading files, writing files, and running shell commands.

## Features

- **Interactive TUI**: Rich terminal interface powered by `prompt-toolkit` with scrollable message history and command shortcuts.
- **Headless & Scripting Mode**: Non-interactive execution for scripts, CI/CD pipelines, and shell pipes.
- **Extensible Command Registry**: Slash command dispatch system (`/help`, `/clear`, `/model`, `/exit`) working in both TUI and Headless modes.
- **Agent Capabilities**: Tool execution for directory navigation, file inspection, file modification, and shell execution (with user approval).
- **Persistent Memory & Logging**: Automatic conversation tracking and structured JSON logging.
- **Mistral AI Integration**: Powered by Mistral LLM models for efficient code assistance.

## Requirements

- **Python**: `>= 3.11`
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv) (recommended)
- **API Key**: A valid [Mistral AI API Key](https://console.mistral.ai/)

## Setup

1. **Configure Environment Variables**:
   Copy the example environment file and set your Mistral API key:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and supply your key:
   ```env
   API_KEY=your_mistral_api_key_here
   ```

2. **Install Dependencies**:
   Install all dependencies using `uv`:
   ```bash
   uv sync
   ```

## Usage

### Running the TUI Application

To launch `cleankoda-cli` with the interactive terminal interface, run:

```bash
uv run cleankoda-cli
```

Alternatively, you can start the module directly:

```bash
uv run python -m cleankoda-cli.tui
```

#### TUI Shortcuts
- **`Enter`**: Send prompt / message
- **`?`**: Toggle help and shortcut overlay
- **`Esc`**: Dismiss shortcut overlay
- **`Ctrl+C`** / **`Ctrl+Q`**: Exit application

---

### Headless Mode (Scripting & CI/CD)

`cleankoda-cli` supports non-interactive execution, ideal for scripts, automated pipelines, or piping text:

- **Positional Prompt Argument**:
  ```bash
  uv run mini-code "Explain the main function in src/mini_code/agent.py"
  ```

- **Prompt Flag (`-p` / `--prompt`)**:
  ```bash
  uv run cleankoda-cli -p "Generate a unit test for memory.py"
  ```

- **Piped Standard Input**:
  ```bash
  cat src/cleankoda-cli/agent.py | uv run cleankoda-cli "Review this file for potential bugs"
  ```

- **Force Execution Mode Flags**:
  - `--headless`: Explicitly force non-interactive headless execution.
  - `--tui`: Explicitly force interactive TUI mode.

---

### Slash Commands (Command Registry)

`cleankoda-cli` includes an extensible command registry. Slash commands work in both TUI mode and Headless mode:

- **`/help`**: Display available commands and their descriptions.
- **`/clear`**: Clear current message memory and start a fresh context.
- **`/model`** or **`/model <name>`**: View the current LLM model or switch to a new model (e.g. `/model mistral-large-latest`).
- **`/exit`** (aliases: `/quit`, `/q`): Exit the application.
