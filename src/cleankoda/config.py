from pathlib import Path

from cleankoda.llm import PROVIDER_MODELS, PROVIDERS
from cleankoda.session_state import SessionState

CONFIG_DIR = Path.home() / ".config" / "cleankoda"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_session_state() -> SessionState:
    """Lädt den SessionState aus CONFIG_FILE."""
    return SessionState.load(file_path=CONFIG_FILE)


def save_session_state(state: SessionState) -> None:
    """Speichert den SessionState in CONFIG_FILE."""
    state.save(file_path=CONFIG_FILE)


def get_provider() -> str | None:
    """Gibt den aktuell konfigurierten Provider zurück."""
    if not CONFIG_FILE.is_file():
        return None
    state = load_session_state()
    return state.provider


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
