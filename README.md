# cleankoda-cli

`cleankoda-cli` is a terminal-based AI coding agent for clean code software development. It features a full TUI (Terminal User Interface) with multi-provider LLM support, interactive tool execution (listing files, reading/writing files, running shell commands), and secure credentials management.

## Features

- **Multi-Provider LLM Support (LiteLLM)**: Seamlessly switch between **Mistral**, **OpenAI**, **Anthropic**, **Ollama**, and **Google Gemini**.
- **Interactive TUI**: Rich terminal interface powered by `prompt-toolkit` with scrollable message history and a 2-line status bar displaying the active Session State (`Provider | Model | Temperature`) and shortcut overlay.
- **Interactive Tool Execution**: Support for tool calling in both TUI streaming and Headless modes for directory listing, file inspection, file modification, and shell command execution (with user approval).
- **Secure Credentials Store**: Secure storage for provider API keys (`~/.config/cleankoda/credentials.json` with `0o600` file permissions) managed interactively via `/provider`.
- **Headless & Scripting Mode**: Non-interactive execution for automated scripts, CI/CD pipelines, and shell pipes.
- **Extensible Command Registry**: Interactive modal dialogs and slash command dispatch system (`/provider`, `/model`, `/temp`, `/help`, `/clear`, `/exit`).
- **Persistent Memory & Logging**: Automatic conversation tracking and structured JSON logging.

## Tech Stack

- **Python** (`>= 3.11`)
- **[Prompt Toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit)**: Terminal User Interface (TUI) layout, keybindings, and interactive modal dialogs.
- **[Rich](https://github.com/Textualize/rich)**: Rich text formatting and terminal output styling.
- **[LiteLLM](https://github.com/BerriAI/litellm)**: Multi-provider LLM integration (Mistral, OpenAI, Anthropic, Ollama, Google Gemini) and tool call streaming.

---

## Getting Started

### Prerequisites

- **Python**: `>= 3.11`
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv) (recommended)
- **API Key(s)**: An API key for your chosen provider (e.g. OpenAI, Anthropic, Mistral, Google Gemini) or a local [Ollama](https://ollama.com/) instance.

### Setup

1. **Install Dependencies**:
   Install all dependencies using `uv`:
   ```bash
   uv sync
   ```

### Usage

#### Running the TUI Application

To launch `cleankoda-cli` with the interactive terminal interface, run:

```bash
uv run cleankoda-cli
```

#### Headless Mode (Scripting & CI/CD)

`cleankoda-cli` supports non-interactive execution, ideal for scripts, automated pipelines, or piping text:

- **Positional Prompt Argument**:
  ```bash
  uv run cleankoda-cli "Explain the main function in src/cleankoda_cli/tui.py"
  ```

- **Prompt Flag (`-p` / `--prompt`)**:
  ```bash
  uv run cleankoda-cli -p "Generate a unit test for memory.py"
  ```

- **Piped Standard Input**:
  ```bash
  cat src/cleankoda_cli/tui.py | uv run cleankoda-cli "Review this file for potential bugs"
  ```

- **Force Execution Mode Flags**:
  - `--headless`: Explicitly force non-interactive headless execution.
  - `--tui`: Explicitly force interactive TUI mode.

---

### Slash Commands (Command Registry)

`cleankoda-cli` includes an extensible command registry. Slash commands work in both TUI mode and Headless mode:

- **`/provider`** or **`/provider <name>`**: Open an interactive selection modal to switch LLM providers (Mistral, OpenAI, Anthropic, Ollama, Google Gemini) and prompt for API keys when required. Automatically switches the model to the primary default model for that provider.
- **`/model`** or **`/model <name>`**: Open an interactive selection modal (filtered for the current provider) or set a specific model.
- **`/temp`** or **`/temp <value>`**: View or adjust the LLM sampling temperature (e.g. `/temp 0.2`).
- **`/help`**: Display available commands and their descriptions.
- **`/clear`**: Clear current message memory and start a fresh context.
- **`/exit`** (aliases: `/quit`, `/q`): Exit the application.
