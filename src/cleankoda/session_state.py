from collections.abc import Callable
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from cleankoda.llm.credentials import CredentialsStore

load_dotenv()

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "cleankoda"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


@dataclass
class StatusManager:
    _slots: dict[str, str] = field(default_factory=dict)
    on_change: Callable[[], None] | None = None

    def set(self, source: str, message: str) -> None:
        """Sets or updates the status of a source and notifies observers."""
        if self._slots.get(source) != message:
            self._slots[source] = message
            self._notify()

    def clear(self, source: str) -> None:
        """Removes the status of a source."""
        if source in self._slots:
            del self._slots[source]
            self._notify()

    def get_combined_status(self) -> str:
        """Returns active status messages in a formatted, separated by ' | '."""
        if not self._slots:
            return ""
        return " | ".join(self._slots.values())

    def _notify(self) -> None:
        if self.on_change:
            self.on_change()


class SessionState(BaseModel):
    provider: str = "mistral"
    model: str = "mistral-medium-latest"
    temperature: float = 0.2
    max_tokens: int = 4096

    @property
    def litellm_model_identifier(self) -> str:
        """Mappt Provider und Modell auf LiteLLM-kompatible Präfixe."""
        from cleankoda.llm.config import get_provider_config

        provider_lower = self.provider.lower()
        model_str = self.model

        p_config = get_provider_config(provider_lower)
        if p_config and p_config.is_custom:
            if model_str.startswith("openai/"):
                return model_str
            return f"openai/{model_str}"

        if "/" in model_str:
            return model_str

        if provider_lower == "google":
            if model_str.startswith("gemini/") or model_str.startswith("google/"):
                return model_str
            return f"gemini/{model_str}"

        if provider_lower in ["ollama", "openrouter", "anthropic", "openai", "mistral"]:
            return f"{provider_lower}/{model_str}"

        return f"openai/{model_str}"

    def get_active_api_key(self, credentials_file: Path | None = None) -> str | None:
        """Holt den aktiven API-Key über den CredentialsStore."""
        store = CredentialsStore.load(file_path=credentials_file)
        return store.get_key(self.provider)

    @classmethod
    def load(cls, file_path: Path | None = None, credentials_file: Path | None = None) -> "SessionState":
        """Lädt die Konfiguration aus der angegebenen JSON-Datei (mit automatischer Migration von legacy api_keys)."""
        target_file = file_path or DEFAULT_CONFIG_FILE
        if not target_file.is_file():
            return cls()

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return cls()
                data = json.loads(content)

            # Auto-Migration: legacy api_keys aus config.json entfernen & in CredentialsStore übertragen
            legacy_api_keys = data.pop("api_keys", None)
            if isinstance(legacy_api_keys, dict) and legacy_api_keys:
                cred_store = CredentialsStore.load(file_path=credentials_file)
                for prov, key in legacy_api_keys.items():
                    if key and isinstance(key, str):
                        cred_store.keys[prov.lower()] = key
                cred_store.save(file_path=credentials_file)

            state = cls.model_validate(data)
            if legacy_api_keys is not None:
                state.save(file_path=target_file)
            return state
        except Exception:
            return cls()

    def save(self, file_path: Path | None = None) -> None:
        """Speichert die Konfiguration als JSON (Dateirechte 0o600 bei Neuanlage/Speicherung)."""
        target_file = file_path or DEFAULT_CONFIG_FILE
        target_file.parent.mkdir(parents=True, exist_ok=True)

        json_data = self.model_dump_json(indent=2)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(json_data)

        try:
            os.chmod(target_file, 0o600)
        except OSError:
            pass
