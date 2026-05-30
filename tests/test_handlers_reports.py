"""Tests for report command handler helpers."""

from __future__ import annotations

import sqlite3
from datetime import date

from bot04.bot.handlers_reports import (
    ReportMenuResponse,
    build_report_menu_response,
    build_period_report_response,
    build_category_report_response,
    build_investment_report_response,
)
from bot04.database.categories import seed_default_categories
from bot04.database.connection import connect
from bot04.database.schema import init_db
from bot04.database.transactions import create_transaction
from bot04.database.users import get_or_create_user


def setup_connection() -> sqlite3.Connection:
    connection = connect(":memory:")
    init_db(connection)
    return connection


def setup_user(connection: sqlite3.Connection, telegram_user_id: int = 796529359) -> int:
    user = get_or_create_user(connection, telegram_user_id=telegram_user_id)
    seed_default_categories(connection, user.id)
    return user.id


def category_id(connection: sqlite3.Connection, user_id: int, type: str, name: str) -> int:
    row = connection.execute(
        "SELECT id FROM categories WHERE user_id = ? AND type = ? AND name = ?",
        (user_id, type, name),
    ).fetchone()
    assert row is not None
    return row[0]


def add_transaction(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    type: str,
    category_name: str,
    amount: int,
    transaction_date: str,
) -> None:
    create_transaction(
        connection,
        user_id=user_id,
        type=type,
        category_id=category_id(connection, user_id, type, category_name),
        amount=amount,
        note=None,
        asset_name="BTC" if type == "investment" else None,
        transaction_date=transaction_date,
    )


def test_build_today_report_response_formats_daily_report_for_user_transactions() -> None:
    connection = setup_connection()
    user_id = setup_user(connection)
    other_user_id = setup_user(connection, telegram_user_id=123)
    add_transaction(
        connection,
        user_id=user_id,
        type="income",
        category_name="Gaji",
        amount=5_000_000,
        transaction_date="2026-05-30",
    )
    add_transaction(
        connection,
        user_id=user_id,
        type="expense",
        category_name="Makan & Minum",
        amount=25_000,
        transaction_date="2026-05-30",
    )
    add_transaction(
        connection,
        user_id=user_id,
        type="expense",
        category_name="Transportasi",
        amount=15_000,
        transaction_date="2026-05-29",
    )
    add_transaction(
        connection,
        user_id=other_user_id,
        type="expense",
        category_name="Makan & Minum",
        amount=99_000,
        transaction_date="2026-05-30",
    )

    response = build_period_report_response(
        "today",
        connection=connection,
        user_id=user_id,
        current_date=date(2026, 5, 30),
    )

    assert response.text.startswith("📊 Laporan Harian\nPeriode: 30 Mei 2026")
    assert "Pemasukan: Rp5.000.000" in response.text
    assert "Pengeluaran: Rp25.000" in response.text
    assert "Makan & Minum — Rp25.000" in response.text
    assert "Transportasi" not in response.text
    assert "Rp99.000" not in response.text
    assert response.reply_markup is None


def test_build_week_and_month_report_responses_use_expected_period_titles() -> None:
    connection = setup_connection()
    user_id = setup_user(connection)

    week_response = build_period_report_response(
        "week",
        connection=connection,
        user_id=user_id,
        current_date=date(2026, 5, 30),
    )
    month_response = build_period_report_response(
        "month",
        connection=connection,
        user_id=user_id,
        current_date=date(2026, 5, 30),
    )

    assert week_response.text.startswith("📊 Laporan Mingguan\nPeriode: 25 Mei 2026 - 31 Mei 2026")
    assert month_response.text.startswith("📊 Laporan Bulanan\nPeriode: 1 Mei 2026 - 31 Mei 2026")


def test_build_report_menu_response_returns_report_choices_keyboard() -> None:
    response = build_report_menu_response()

    assert response == ReportMenuResponse(
        text="Pilih jenis laporan:",
        reply_markup=response.reply_markup,
    )
    assert response.reply_markup is not None
    assert [[button.text for button in row] for row in response.reply_markup.inline_keyboard] == [
        ["📅 Hari Ini", "🗓 Minggu Ini"],
        ["📆 Bulan Ini"],
        ["🗂 Kategori Pemasukan", "🗂 Kategori Pengeluaran"],
        ["📈 Investasi"],
    ]


def test_build_category_report_response_formats_income_or_expense_totals() -> None:
    connection = setup_connection()
    user_id = setup_user(connection)
    add_transaction(
        connection,
        user_id=user_id,
        type="income",
        category_name="Gaji",
        amount=5_000_000,
        transaction_date="2026-05-30",
    )
    add_transaction(
        connection,
        user_id=user_id,
        type="income",
        category_name="Bonus",
        amount=100_000,
        transaction_date="2026-05-30",
    )
    add_transaction(
        connection,
        user_id=user_id,
        type="expense",
        category_name="Makan & Minum",
        amount=25_000,
        transaction_date="2026-05-30",
    )

    response = build_category_report_response(
        "income",
        connection=connection,
        user_id=user_id,
        current_date=date(2026, 5, 30),
    )

    assert response.text == (
        "🗂 Kategori Pemasukan\n"
        "1. Gaji — Rp5.000.000\n"
        "2. Bonus — Rp100.000"
    )


def test_build_investment_report_response_formats_investment_summary() -> None:
    connection = setup_connection()
    user_id = setup_user(connection)
    add_transaction(
        connection,
        user_id=user_id,
        type="income",
        category_name="Gaji",
        amount=5_000_000,
        transaction_date="2026-05-30",
    )
    add_transaction(
        connection,
        user_id=user_id,
        type="investment",
        category_name="Crypto",
        amount=1_000_000,
        transaction_date="2026-05-30",
    )

    response = build_investment_report_response(
        connection=connection,
        user_id=user_id,
        current_date=date(2026, 5, 30),
    )

    assert response.text == (
        "📈 Laporan Investasi\n"
        "Total Investasi: Rp1.000.000\n"
        "Persentase dari Pemasukan: 20.00%"
    )
