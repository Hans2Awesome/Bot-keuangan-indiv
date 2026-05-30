"""Configuration loading for Bot04."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """Application configuration values."""

    bot_token: str
    database_path: str
    timezone: str
    currency: str


def _env_value(name: str, default: str) -> str:
    """Read and normalize one environment value."""

    return os.getenv(name, default).strip()


def load_config(*, load_dotenv_file: bool = True) -> Config:
    """Load configuration from environment and optional .env file.

    Args:
        load_dotenv_file: When true, load values from a local ``.env`` file before
            reading environment variables. Tests can disable this for isolation.
    """

    if load_dotenv_file:
        load_dotenv()

    return Config(
        bot_token=_env_value("BOT_TOKEN", ""),
        database_path=_env_value("DATABASE_PATH", "bot04.sqlite3"),
        timezone=_env_value("TIMEZONE", "Asia/Jakarta"),
        currency=_env_value("CURRENCY", "IDR"),
    )
