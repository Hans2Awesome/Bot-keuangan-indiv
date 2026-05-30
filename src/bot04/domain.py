"""Domain types for Bot04."""

from __future__ import annotations

from enum import StrEnum


class TransactionType(StrEnum):
    """Supported transaction type values."""

    INCOME = "income"
    EXPENSE = "expense"
    INVESTMENT = "investment"


_TRANSACTION_TYPE_LABELS: dict[TransactionType, str] = {
    TransactionType.INCOME: "Pemasukan",
    TransactionType.EXPENSE: "Pengeluaran",
    TransactionType.INVESTMENT: "Investasi",
}


def valid_transaction_type_values() -> set[str]:
    """Return all supported transaction type values."""

    return {transaction_type.value for transaction_type in TransactionType}


def transaction_type_label(transaction_type: TransactionType | str) -> str:
    """Return the Indonesian display label for a transaction type."""

    return _TRANSACTION_TYPE_LABELS[TransactionType(transaction_type)]
