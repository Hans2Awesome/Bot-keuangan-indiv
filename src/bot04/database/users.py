"""User repository for Bot04."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    """A Bot04 user persisted in SQLite."""

    id: int
    telegram_user_id: int
    first_name: str | None
    username: str | None
    timezone: str
    currency: str


def _row_to_user(row: sqlite3.Row | tuple) -> User:
    """Convert a SQLite user row into a User object."""

    return User(
        id=row["id"],
        telegram_user_id=row["telegram_user_id"],
        first_name=row["first_name"],
        username=row["username"],
        timezone=row["timezone"],
        currency=row["currency"],
    )


def _fetch_user_by_telegram_id(
    connection: sqlite3.Connection,
    telegram_user_id: int,
) -> User | None:
    row = connection.execute(
        """
        SELECT id, telegram_user_id, first_name, username, timezone, currency
        FROM users
        WHERE telegram_user_id = ?
        """,
        (telegram_user_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_user(row)


def get_or_create_user(
    connection: sqlite3.Connection,
    *,
    telegram_user_id: int,
    first_name: str | None = None,
    username: str | None = None,
    timezone: str = "Asia/Jakarta",
    currency: str = "IDR",
) -> User:
    """Return the existing user for a Telegram ID or create it once."""

    connection.row_factory = sqlite3.Row

    existing_user = _fetch_user_by_telegram_id(connection, telegram_user_id)
    if existing_user is not None:
        return existing_user

    connection.execute(
        """
        INSERT INTO users (telegram_user_id, first_name, username, timezone, currency)
        VALUES (?, ?, ?, ?, ?)
        """,
        (telegram_user_id, first_name, username, timezone, currency),
    )
    connection.commit()

    created_user = _fetch_user_by_telegram_id(connection, telegram_user_id)
    if created_user is None:
        raise RuntimeError("Failed to create user")
    return created_user
