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
