import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "cleankoda"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


class SessionState(BaseModel):
    provider: str = "mistral"
    model: str = "mistral-medium-latest"
    temperature: float = 0.2
    max_tokens: int = 4096
    api_keys: dict[str, str] = Field(default_factory=dict)

    @property
    def litellm_model_identifier(self) -> str:
        """Mappt Provider und Modell auf LiteLLM-kompatible Präfixe."""
        provider_lower = self.provider.lower()
        model_str = self.model

        if "/" in model_str:
            return model_str

        if provider_lower == "google":
            if model_str.startswith("gemini/") or model_str.startswith("google/"):
                return model_str
            return f"gemini/{model_str}"

        if provider_lower in ["ollama", "openrouter", "anthropic", "openai", "mistral"]:
            return f"{provider_lower}/{model_str}"

        return f"{provider_lower}/{model_str}"

    def get_active_api_key(self) -> str | None:
        """Priorisiert OS-Environment-Variablen vor den in api_keys hinterlegten Werten."""
        provider_lower = self.provider.lower()

        env_key_map: dict[str, list[str]] = {
            "anthropic": ["ANTHROPIC_API_KEY"],
            "openai": ["OPENAI_API_KEY"],
            "mistral": ["MISTRAL_API_KEY"],
            "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
            "openrouter": ["OPENROUTER_API_KEY"],
            "ollama": ["OLLAMA_API_KEY"],
        }

        keys_to_check = env_key_map.get(provider_lower, [f"{provider_lower.upper()}_API_KEY"])
        for env_var in keys_to_check:
            val = os.getenv(env_var)
            if val:
                return val

        return self.api_keys.get(self.provider) or self.api_keys.get(provider_lower)

    @classmethod
    def load(cls, file_path: Path | None = None) -> "SessionState":
        """Lädt die Konfiguration aus der angegebenen JSON-Datei oder der Standardkonfigurationsdatei."""
        target_file = file_path or DEFAULT_CONFIG_FILE
        if not target_file.is_file():
            return cls()

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return cls()
                return cls.model_validate_json(content)
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
