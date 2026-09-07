from pathlib import Path

from cleankoda.llm import get_models_for_provider as fetch_models_for_provider
from cleankoda.session_state import SessionState

CONFIG_DIR = Path.home() / ".config" / "cleankoda"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_session_state() -> SessionState:
    """Loads the session state from CONFIG_FILE."""
    return SessionState.load(file_path=CONFIG_FILE)


def save_session_state(state: SessionState) -> None:
    """Stores the session state in CONFIG_FILE."""
    state.save(file_path=CONFIG_FILE)


def get_provider() -> str | None:
    """Returns the currently configured provider."""
    if not CONFIG_FILE.is_file():
        return None
    state = load_session_state()
    return state.provider


def set_provider(provider_name: str) -> None:
    """Set the provider in the configuration and save it.
    Set the model to the first model in the list of the respective provider.
    """
    state = load_session_state()
    state.provider = provider_name
    models = get_models_for_provider(provider_name)
    if models:
        state.model = models[0]
    save_session_state(state)


def get_models_for_provider(provider_name: str | None = None) -> list[str]:
    """Returns the list of available models for a provider."""
    if not provider_name:
        provider_name = get_provider() or "mistral"
    return fetch_models_for_provider(provider_name)


def get_model() -> str:
    """Gibt das aktuell konfigurierte LLM-Modell zurück."""
    state = load_session_state()
    return state.model


def set_model(model_name: str) -> None:
    """Setzt das Modell in der Konfiguration und speichert diese."""
    state = load_session_state()
    state.model = model_name
    save_session_state(state)
