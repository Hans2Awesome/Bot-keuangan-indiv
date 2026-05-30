"""SQLite connection helpers for Bot04."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(database_path: str | Path) -> sqlite3.Connection:
    """Create a SQLite connection configured for Bot04."""

    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
