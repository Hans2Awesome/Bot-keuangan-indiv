"""Service layer for saving confirmed transaction previews."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from bot04.database.transactions import create_transaction
from bot04.services.quick_input_parser import QuickInputResult


class TransactionServiceError(ValueError):
    """Raised when a confirmed preview cannot be saved."""


@dataclass(frozen=True)
class SavedTransactionSummary:
    """Summary of a transaction saved from a confirmed preview."""

    id: int
    type: str
    category_name: str
    amount: int
    note: str | None
    asset_name: str | None
    transaction_date: str


@dataclass(frozen=True)
class _ValidatedPreview:
    type: str
    category_name: str
    amount: int
    note: str
    asset_name: str | None
    transaction_date: str


def save_confirmed_transaction(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    preview: QuickInputResult,
) -> SavedTransactionSummary:
    """Save a confirmed quick-input preview as a transaction."""

    validated = _validate_preview(preview)
    category_id = _find_category_id(
        connection,
        user_id=user_id,
        type=validated.type,
        category_name=validated.category_name,
    )
    if category_id is None:
        raise TransactionServiceError("Kategori tidak valid untuk user ini.")

    transaction = create_transaction(
        connection,
        user_id=user_id,
        type=validated.type,
        category_id=category_id,
        amount=validated.amount,
        note=validated.note or None,
        asset_name=validated.asset_name,
        transaction_date=validated.transaction_date,
    )

    return SavedTransactionSummary(
        id=transaction.id,
        type=transaction.type,
        category_name=validated.category_name,
        amount=transaction.amount,
        note=transaction.note,
        asset_name=transaction.asset_name,
        transaction_date=transaction.transaction_date,
    )


def _validate_preview(preview: QuickInputResult) -> _ValidatedPreview:
    if preview.error:
        raise TransactionServiceError("Preview belum valid dan belum bisa disimpan.")
    if (
        preview.type is None
        or preview.category_name is None
        or preview.amount is None
        or preview.transaction_date is None
    ):
        raise TransactionServiceError("Preview belum valid dan belum bisa disimpan.")
    return _ValidatedPreview(
        type=preview.type,
        category_name=preview.category_name,
        amount=preview.amount,
        note=preview.note,
        asset_name=preview.asset_name,
        transaction_date=preview.transaction_date.isoformat(),
    )


def _find_category_id(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    type: str,
    category_name: str,
) -> int | None:
    row = connection.execute(
        """
        SELECT id
        FROM categories
        WHERE user_id = ? AND type = ? AND name = ?
        """,
        (user_id, type, category_name),
    ).fetchone()
    if row is None:
        return None
    return row[0]
