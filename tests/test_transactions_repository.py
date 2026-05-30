"""Tests for Bot04 transaction repository."""

from __future__ import annotations

import sqlite3

from bot04.database.categories import seed_default_categories
from bot04.database.connection import connect
from bot04.database.schema import init_db
from bot04.database.transactions import (
    Transaction,
    create_transaction,
    delete_transaction,
    list_transactions,
    update_transaction,
)
from bot04.database.users import get_or_create_user


def setup_connection() -> sqlite3.Connection:
    connection = connect(":memory:")
    init_db(connection)
    return connection


def setup_user_with_categories(
    connection: sqlite3.Connection,
    telegram_user_id: int,
) -> tuple[int, int]:
    user = get_or_create_user(connection, telegram_user_id=telegram_user_id)
    seed_default_categories(connection, user.id)
    category_id = connection.execute(
        """
        SELECT id FROM categories
        WHERE user_id = ? AND type = 'expense' AND name = 'Makan & Minum'
        """,
        (user.id,),
    ).fetchone()[0]
    return user.id, category_id


def test_create_transaction_persists_and_returns_transaction() -> None:
    connection = setup_connection()
    user_id, category_id = setup_user_with_categories(connection, 796529359)

    transaction = create_transaction(
        connection,
        user_id=user_id,
        type="expense",
        category_id=category_id,
        amount=25000,
        note="kopi pagi",
        asset_name=None,
        transaction_date="2026-05-30",
    )

    assert transaction == Transaction(
        id=1,
        user_id=user_id,
        type="expense",
        category_id=category_id,
        amount=25000,
        note="kopi pagi",
        asset_name=None,
        transaction_date="2026-05-30",
    )
    row_count = connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    assert row_count == 1


def test_list_transactions_filters_by_user_and_date_range() -> None:
    connection = setup_connection()
    first_user_id, first_category_id = setup_user_with_categories(connection, 1)
    second_user_id, second_category_id = setup_user_with_categories(connection, 2)
    expected = create_transaction(
        connection,
        user_id=first_user_id,
        type="expense",
        category_id=first_category_id,
        amount=10000,
        note="inside range",
        asset_name=None,
        transaction_date="2026-05-15",
    )
    create_transaction(
        connection,
        user_id=first_user_id,
        type="expense",
        category_id=first_category_id,
        amount=20000,
        note="outside range",
        asset_name=None,
        transaction_date="2026-06-01",
    )
    create_transaction(
        connection,
        user_id=second_user_id,
        type="expense",
        category_id=second_category_id,
        amount=30000,
        note="other user",
        asset_name=None,
        transaction_date="2026-05-15",
    )

    transactions = list_transactions(
        connection,
        user_id=first_user_id,
        start_date="2026-05-01",
        end_date="2026-05-31",
    )

    assert transactions == [expected]


def test_update_transaction_changes_only_owned_transaction_fields() -> None:
    connection = setup_connection()
    user_id, category_id = setup_user_with_categories(connection, 1)
    other_user_id, other_category_id = setup_user_with_categories(connection, 2)
    transaction = create_transaction(
        connection,
        user_id=user_id,
        type="expense",
        category_id=category_id,
        amount=10000,
        note="old note",
        asset_name=None,
        transaction_date="2026-05-15",
    )
    other_transaction = create_transaction(
        connection,
        user_id=other_user_id,
        type="expense",
        category_id=other_category_id,
        amount=99999,
        note="do not touch",
        asset_name=None,
        transaction_date="2026-05-15",
    )

    updated = update_transaction(
        connection,
        user_id=user_id,
        transaction_id=transaction.id,
        amount=15000,
        category_id=category_id,
        transaction_date="2026-05-16",
        note="updated note",
    )
    blocked_update = update_transaction(
        connection,
        user_id=user_id,
        transaction_id=other_transaction.id,
        amount=1,
        category_id=category_id,
        transaction_date="2026-05-17",
        note="leak attempt",
    )

    assert updated == Transaction(
        id=transaction.id,
        user_id=user_id,
        type="expense",
        category_id=category_id,
        amount=15000,
        note="updated note",
        asset_name=None,
        transaction_date="2026-05-16",
    )
    assert blocked_update is None


def test_delete_transaction_removes_only_owned_transaction() -> None:
    connection = setup_connection()
    user_id, category_id = setup_user_with_categories(connection, 1)
    other_user_id, other_category_id = setup_user_with_categories(connection, 2)
    transaction = create_transaction(
        connection,
        user_id=user_id,
        type="expense",
        category_id=category_id,
        amount=10000,
        note="delete me",
        asset_name=None,
        transaction_date="2026-05-15",
    )
    other_transaction = create_transaction(
        connection,
        user_id=other_user_id,
        type="expense",
        category_id=other_category_id,
        amount=20000,
        note="keep me",
        asset_name=None,
        transaction_date="2026-05-15",
    )

    assert delete_transaction(connection, user_id=user_id, transaction_id=other_transaction.id) is False
    assert delete_transaction(connection, user_id=user_id, transaction_id=transaction.id) is True

    assert list_transactions(
        connection,
        user_id=user_id,
        start_date="2026-05-01",
        end_date="2026-05-31",
    ) == []
    assert list_transactions(
        connection,
        user_id=other_user_id,
        start_date="2026-05-01",
        end_date="2026-05-31",
    ) == [other_transaction]
