import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "cleankoda"
CUSTOM_CONFIG_FILE = CONFIG_DIR / "custom.json"


class ProviderConfig(BaseModel):
    key: str
    name: str
    api_base: str | None = None
    is_custom: bool = False
    requires_api_key: bool = True
    models: list[str] = Field(default_factory=list)


BUILTIN_PROVIDERS: dict[str, ProviderConfig] = {
    "mistral": ProviderConfig(
        key="mistral",
        name="Mistral",
        models=[
            "mistral-small-latest",
            "mistral-medium-latest",
            "mistral-large-latest",
            "codestral-latest",
        ],
    ),
    "openai": ProviderConfig(
        key="openai",
        name="OpenAI",
        models=[
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "o1-mini",
            "o3-mini",
        ],
    ),
    "anthropic": ProviderConfig(
        key="anthropic",
        name="Anthropic",
        models=[
            "claude-3-5-sonnet-latest",
            "claude-3-5-haiku-latest",
            "claude-3-opus-latest",
        ],
    ),
    "ollama": ProviderConfig(
        key="ollama",
        name="Ollama (Lokal)",
        api_base="http://localhost:11434/v1",
        requires_api_key=False,
        models=[
            "llama3.3",
            "qwen2.5-coder",
            "deepseek-r1",
            "mistral",
        ],
    ),
    "google": ProviderConfig(
        key="google",
        name="Google Gemini",
        models=[
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-1.5-pro",
        ],
    ),
}

# Backwards compatibility constants
PROVIDERS = list(BUILTIN_PROVIDERS.keys())
PROVIDER_MODELS = {k: v.models for k, v in BUILTIN_PROVIDERS.items()}


def create_example_custom_config(file_path: Path) -> None:
    """Erstellt eine Beispieldatei für custom.json."""
    example_content = {
        "gcp_serverless": {
            "name": "GCP Private LLM",
            "api_base": "https://my-llm-service-xyz.a.run.app/v1",
            "models": ["qwen2.5-coder:32b", "mistral-large"],
            "requires_api_key": True,
        },
        "ollama": {
            "name": "Ollama (Lokal)",
            "api_base": "http://localhost:11434/v1",
            "models": ["qwen2.5-coder:7b", "llama3.1:8b"],
            "requires_api_key": False,
        },
    }
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(example_content, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not create example custom.json at {file_path}: {e}")


def load_provider_registry(custom_file_path: Path | None = None) -> dict[str, ProviderConfig]:
    """Lädt die Provider-Registry aus Built-in-Providern und custom.json."""
    target_file = custom_file_path or CUSTOM_CONFIG_FILE
    registry = {k: v.model_copy() for k, v in BUILTIN_PROVIDERS.items()}

    if not target_file.is_file():
        if custom_file_path is None:
            example_file = target_file.parent / "custom.json.example"
            if not example_file.exists():
                create_example_custom_config(example_file)
        return registry

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return registry
            data = json.loads(content)

        if not isinstance(data, dict):
            logger.warning(f"Invalid format in {target_file}: expected dict at root level.")
            return registry

        for raw_key, provider_data in data.items():
            if not isinstance(provider_data, dict):
                continue
            key = raw_key.lower().strip()
            name = provider_data.get("name", key)
            api_base = provider_data.get("api_base")
            models = provider_data.get("models", [])
            requires_api_key = provider_data.get("requires_api_key", True)
            is_custom = provider_data.get("is_custom", True)

            if key in BUILTIN_PROVIDERS:
                builtin = registry[key]
                registry[key] = ProviderConfig(
                    key=key,
                    name=name if "name" in provider_data else builtin.name,
                    api_base=api_base if "api_base" in provider_data else builtin.api_base,
                    is_custom=is_custom if "is_custom" in provider_data else builtin.is_custom,
                    requires_api_key=requires_api_key if "requires_api_key" in provider_data else builtin.requires_api_key,
                    models=models if "models" in provider_data else builtin.models,
                )
            else:
                registry[key] = ProviderConfig(
                    key=key,
                    name=name,
                    api_base=api_base,
                    is_custom=is_custom,
                    requires_api_key=requires_api_key,
                    models=models,
                )

    except json.JSONDecodeError as e:
        logger.warning(f"Error reading {target_file}: Invalid JSON format - {e}")
    except Exception as e:
        logger.warning(f"Error loading custom providers from {target_file}: {e}")

    return registry


def get_provider_configs(custom_file_path: Path | None = None) -> dict[str, ProviderConfig]:
    """Gibt alle registrierten ProviderConfig-Objekte zurück."""
    return load_provider_registry(custom_file_path=custom_file_path)


def get_available_providers(custom_file_path: Path | None = None) -> list[str]:
    """Gibt die Liste aller verfügbaren Provider-Keys zurück."""
    registry = load_provider_registry(custom_file_path=custom_file_path)
    return list(registry.keys())


def get_provider_config(provider_key: str, custom_file_path: Path | None = None) -> ProviderConfig | None:
    """Gibt die ProviderConfig für den angegebenen Provider-Key zurück."""
    registry = load_provider_registry(custom_file_path=custom_file_path)
    return registry.get(provider_key.lower())


def get_models_for_provider(
    provider_key: str | None = None, custom_file_path: Path | None = None
) -> list[str]:
    """Gibt die Modellliste für den angegebenen Provider zurück."""
    registry = load_provider_registry(custom_file_path=custom_file_path)
    if not provider_key:
        provider_key = "mistral"
    p_config = registry.get(provider_key.lower())
    if p_config and p_config.models:
        return p_config.models
    default_config = registry.get("mistral")
    return default_config.models if default_config else []
