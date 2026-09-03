import json
from pathlib import Path
from typing import Any

import cleankoda_cli.llm as llm_module

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


def load_config() -> dict[str, Any]:
    """Lädt die Konfiguration aus ~/.config/cleankoda/config.json."""
    if not CONFIG_FILE.is_file():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(config_data: dict[str, Any]) -> None:
    """Speichert die Konfiguration in ~/.config/cleankoda/config.json (erstellt Ordner/Datei falls nicht vorhanden)."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)


def get_provider() -> str | None:
    """Gibt den aktuell konfigurierten Provider zurück."""
    config = load_config()
    return config.get("provider")


def set_provider(provider_name: str) -> None:
    """Setzt den Provider in der Konfiguration und speichert diese."""
    config = load_config()
    config["provider"] = provider_name
    save_config(config)


def get_models_for_provider(provider_name: str | None = None) -> list[str]:
    """Gibt die Liste der verfügbaren Modelle für einen bestimmten Provider zurück (Standard: aktueller Provider oder mistral)."""
    if not provider_name:
        provider_name = get_provider() or "mistral"
    return PROVIDER_MODELS.get(provider_name.lower(), PROVIDER_MODELS["mistral"])


def get_model() -> str:
    """Gibt das aktuell konfigurierte LLM-Modell zurück (Standard: llm_module.model_name)."""
    config = load_config()
    return config.get("model", getattr(llm_module, "model_name", "mistral-medium-latest"))


def set_model(model_name: str) -> None:
    """Setzt das Modell in der Konfiguration und aktualisiert llm_module.model_name."""
    config = load_config()
    config["model"] = model_name
    save_config(config)
    llm_module.model_name = model_name
