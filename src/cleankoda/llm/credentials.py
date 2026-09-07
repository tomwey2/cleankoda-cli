import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

DEFAULT_CREDENTIALS_DIR = Path.home() / ".config" / "cleankoda"
DEFAULT_CREDENTIALS_FILE = DEFAULT_CREDENTIALS_DIR / "credentials.json"


class CredentialsStore(BaseModel):
    keys: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def load(cls, file_path: Path | None = None) -> "CredentialsStore":
        """Lädt die Anmeldedaten aus der angegebenen Datei oder der Standard-Credentials-Datei."""
        target_file = file_path or DEFAULT_CREDENTIALS_FILE
        if not target_file.is_file():
            return cls()

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return cls()
                data = json.loads(content)
                if isinstance(data, dict):
                    # Direct dict mapping or nested {"keys": {...}}
                    if "keys" in data and isinstance(data["keys"], dict):
                        return cls(keys=data["keys"])
                    return cls(keys=data)
                return cls()
        except Exception:
            return cls()

    def save(self, file_path: Path | None = None) -> None:
        """Speichert die Anmeldedaten als JSON (Dateirechte 0o600)."""
        target_file = file_path or DEFAULT_CREDENTIALS_FILE
        target_file.parent.mkdir(parents=True, exist_ok=True)

        json_data = self.model_dump_json(indent=2)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(json_data)

        try:
            os.chmod(target_file, 0o600)
        except OSError:
            pass

    def get_stored_key(self, provider: str) -> str | None:
        """Gibt den direkt in credentials.json gespeicherten Key zurück."""
        return self.keys.get(provider.lower())

    def get_key(self, provider: str) -> str | None:
        """Priorisiert OS-Environment-Variablen vor den in credentials.json gespeicherten Keys."""
        provider_lower = provider.lower()

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

        return self.get_stored_key(provider_lower)

    def set_key(self, provider: str, api_key: str, file_path: Path | None = None) -> None:
        """Setzt einen neuen API-Key für den Provider und speichert die Datei."""
        self.keys[provider.lower()] = api_key
        self.save(file_path=file_path)
