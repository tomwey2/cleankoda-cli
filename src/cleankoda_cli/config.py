import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "cleankoda"
CONFIG_FILE = CONFIG_DIR / "config.json"

PROVIDERS = ["mistral", "openai", "anthropic", "ollama", "google"]


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
