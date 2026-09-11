import pytest


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    # Automatically redirects all config files to temporary Pytest directory
    monkeypatch.setenv("CLEANKODA_CONFIG_DIR", str(tmp_path))
