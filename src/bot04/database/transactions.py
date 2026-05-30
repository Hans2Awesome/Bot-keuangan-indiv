"""Transaction repository for Bot04."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Transaction:
    """A Bot04 financial transaction persisted in SQLite."""

    id: int
    user_id: int
    type: str
    category_id: int | None
    amount: int
    note: str | None
    asset_name: str | None
    transaction_date: str


def _configure_rows(connection: sqlite3.Connection) -> None:
    connection.row_factory = sqlite3.Row


def _row_to_transaction(row: sqlite3.Row) -> Transaction:
    return Transaction(
        id=row["id"],
        user_id=row["user_id"],
        type=row["type"],
        category_id=row["category_id"],
        amount=row["amount"],
        note=row["note"],
        asset_name=row["asset_name"],
        transaction_date=row["transaction_date"],
    )


def _fetch_transaction(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    transaction_id: int,
) -> Transaction | None:
    _configure_rows(connection)
    row = connection.execute(
        """
        SELECT id, user_id, type, category_id, amount, note, asset_name, transaction_date
        FROM transactions
        WHERE id = ? AND user_id = ?
        """,
        (transaction_id, user_id),
    ).fetchone()
    if row is None:
        return None
    return _row_to_transaction(row)


def create_transaction(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    type: str,
    category_id: int | None,
    amount: int,
    note: str | None,
    asset_name: str | None,
    transaction_date: str,
) -> Transaction:
    """Create and return a transaction for one user."""

    _configure_rows(connection)
    cursor = connection.execute(
        """
        INSERT INTO transactions (
            user_id, type, category_id, amount, note, asset_name, transaction_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, type, category_id, amount, note, asset_name, transaction_date),
    )
    connection.commit()

    transaction = _fetch_transaction(
        connection,
        user_id=user_id,
        transaction_id=cursor.lastrowid,
    )
    if transaction is None:
        raise RuntimeError("Failed to create transaction")
    return transaction


def list_transactions(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    start_date: str,
    end_date: str,
) -> list[Transaction]:
    """List one user's transactions within an inclusive date range."""

    _configure_rows(connection)
    rows = connection.execute(
        """
        SELECT id, user_id, type, category_id, amount, note, asset_name, transaction_date
        FROM transactions
        WHERE user_id = ? AND transaction_date BETWEEN ? AND ?
        ORDER BY transaction_date ASC, id ASC
        """,
        (user_id, start_date, end_date),
    ).fetchall()
    return [_row_to_transaction(row) for row in rows]


def update_transaction(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    transaction_id: int,
    amount: int,
    category_id: int | None,
    transaction_date: str,
    note: str | None,
) -> Transaction | None:
    """Update editable fields for one owned transaction."""

    connection.execute(
        """
        UPDATE transactions
        SET amount = ?, category_id = ?, transaction_date = ?, note = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND user_id = ?
        """,
        (amount, category_id, transaction_date, note, transaction_id, user_id),
    )
    connection.commit()
    return _fetch_transaction(connection, user_id=user_id, transaction_id=transaction_id)


def delete_transaction(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    transaction_id: int,
) -> bool:
    """Delete one owned transaction and report whether anything was removed."""

    cursor = connection.execute(
        """
        DELETE FROM transactions
        WHERE id = ? AND user_id = ?
        """,
        (transaction_id, user_id),
    )
    connection.commit()
    return cursor.rowcount == 1
