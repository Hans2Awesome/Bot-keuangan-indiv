"""Smoke tests for the initial Bot04 project structure."""

from bot04 import __version__
from bot04.config import load_config


def test_package_imports() -> None:
    assert __version__ == "0.1.0"


def test_default_config_loads() -> None:
    config = load_config()

    assert config.database_path
    assert config.timezone == "Asia/Jakarta"
    assert config.currency == "IDR"
