import json
from pathlib import Path
from typing import Any

from cleankoda_cli.session_state import SessionState

CONFIG_DIR = Path.home() / ".config" / "cleankoda"
CONFIG_FILE = CONFIG_DIR / "config.json"

PROVIDERS = ["mistral", "openai", "anthropic", "ollama", "google"]

PROVIDER_MODELS: dict[str, list[str]] = {
    "mistral": [
        "mistral-small-latest",
        "mistral-medium-latest",
        "mistral-large-latest",
        "codestral-latest",
    ],
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "o1-mini",
        "o3-mini",
    ],
    "anthropic": [
        "claude-3-5-sonnet-latest",
        "claude-3-5-haiku-latest",
        "claude-3-opus-latest",
    ],
    "ollama": [
        "llama3.3",
        "qwen2.5-coder",
        "deepseek-r1",
        "mistral",
    ],
    "google": [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-1.5-pro",
    ],
}


def load_session_state() -> SessionState:
    """Lädt den SessionState aus CONFIG_FILE."""
    return SessionState.load(file_path=CONFIG_FILE)


def save_session_state(state: SessionState) -> None:
    """Speichert den SessionState in CONFIG_FILE."""
    state.save(file_path=CONFIG_FILE)


def load_config() -> dict[str, Any]:
    """Lädt die Konfiguration aus CONFIG_FILE."""
    if not CONFIG_FILE.is_file():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(config_data: dict[str, Any]) -> None:
    """Speichert ein Dict in CONFIG_FILE."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)


def get_provider() -> str | None:
    """Gibt den aktuell konfigurierten Provider zurück."""
    config = load_config()
    return config.get("provider")


def set_provider(provider_name: str) -> None:
    """Setzt den Provider in der Konfiguration und speichert diese.
    Setzt das Modell auf das erste Modell in der Liste des jeweiligen Providers.
    """
    state = load_session_state()
    state.provider = provider_name
    models = get_models_for_provider(provider_name)
    if models:
        state.model = models[0]
    save_session_state(state)


def get_models_for_provider(provider_name: str | None = None) -> list[str]:
    """Gibt die Liste der verfügbaren Modelle für einen Provider zurück."""
    if not provider_name:
        provider_name = get_provider() or "mistral"
    return PROVIDER_MODELS.get(provider_name.lower(), PROVIDER_MODELS["mistral"])


def get_model() -> str:
    """Gibt das aktuell konfigurierte LLM-Modell zurück."""
    state = load_session_state()
    return state.model


def set_model(model_name: str) -> None:
    """Setzt das Modell in der Konfiguration und speichert diese."""
    state = load_session_state()
    state.model = model_name
    save_session_state(state)
