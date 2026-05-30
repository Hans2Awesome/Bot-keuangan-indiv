"""Tests for Bot04 SQLite schema initialization."""

from __future__ import annotations

import sqlite3

import pytest

from bot04.database.connection import connect
from bot04.database.schema import init_db


def table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row[0] for row in rows}


def column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def test_init_db_creates_core_tables() -> None:
    connection = connect(":memory:")

    init_db(connection)

    assert table_names(connection) == {"users", "categories", "transactions", "wallets"}


def test_init_db_creates_expected_columns() -> None:
    connection = connect(":memory:")

    init_db(connection)

    assert column_names(connection, "users") == {
        "id",
        "telegram_user_id",
        "first_name",
        "username",
        "timezone",
        "currency",
        "created_at",
    }
    assert column_names(connection, "categories") == {
        "id",
        "user_id",
        "type",
        "name",
        "aliases",
        "is_default",
    }
    assert column_names(connection, "transactions") == {
        "id",
        "user_id",
        "type",
        "category_id",
        "amount",
        "note",
        "asset_name",
        "transaction_date",
        "created_at",
        "updated_at",
    }


def test_users_telegram_user_id_must_be_unique() -> None:
    connection = connect(":memory:")
    init_db(connection)

    connection.execute(
        """
        INSERT INTO users (telegram_user_id, first_name, username, timezone, currency)
        VALUES (?, ?, ?, ?, ?)
        """,
        (796529359, "Hans", "hans", "Asia/Jakarta", "IDR"),
    )

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO users (telegram_user_id, first_name, username, timezone, currency)
            VALUES (?, ?, ?, ?, ?)
            """,
            (796529359, "Hans Duplicate", "hans2", "Asia/Jakarta", "IDR"),
        )


def test_categories_are_unique_per_user_type_and_name() -> None:
    connection = connect(":memory:")
    init_db(connection)
    cursor = connection.execute(
        """
        INSERT INTO users (telegram_user_id, first_name, username, timezone, currency)
        VALUES (?, ?, ?, ?, ?)
        """,
        (1, "User", "user", "Asia/Jakarta", "IDR"),
    )
    user_id = cursor.lastrowid

    connection.execute(
        """
        INSERT INTO categories (user_id, type, name, aliases, is_default)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, "expense", "Makan", "makan,kopi", 1),
    )

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO categories (user_id, type, name, aliases, is_default)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, "expense", "Makan", "sarapan", 0),
        )
