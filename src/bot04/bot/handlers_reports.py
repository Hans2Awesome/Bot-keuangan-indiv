"""Report command handler helpers for Bot04 Telegram bot."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot04.database.transactions import Transaction, list_transactions
from bot04.domain import transaction_type_label
from bot04.reports.aggregator import CategoryTotal, aggregate_transactions
from bot04.reports.date_ranges import DateRange, month_range, today_range, week_range
from bot04.reports.formatter import (
    format_category_report,
    format_investment_report,
    format_period_report,
)

CALLBACK_REPORT_TODAY = "report_today"
CALLBACK_REPORT_WEEK = "report_week"
CALLBACK_REPORT_MONTH = "report_month"
CALLBACK_REPORT_INCOME_CATEGORIES = "report_income_categories"
CALLBACK_REPORT_EXPENSE_CATEGORIES = "report_expense_categories"
CALLBACK_REPORT_INVESTMENT = "report_investment"


@dataclass(frozen=True)
class ReportMenuResponse:
    """Telegram message payload for report handlers."""

    text: str
    reply_markup: InlineKeyboardMarkup | None


def build_period_report_response(
    period: str,
    *,
    connection: sqlite3.Connection,
    user_id: int,
    current_date: date,
) -> ReportMenuResponse:
    """Build today, week, or month report text for one user."""

    title, date_range = _period_title_and_range(period, current_date)
    transactions = _transactions_for_range(connection, user_id=user_id, date_range=date_range)
    summary = aggregate_transactions(
        transactions,
        category_names=_category_names_for(connection, user_id=user_id),
    )
    return ReportMenuResponse(
        text=format_period_report(title=title, date_range=date_range, summary=summary),
        reply_markup=None,
    )


def build_report_menu_response() -> ReportMenuResponse:
    """Build a report menu with choices for /report."""

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📅 Hari Ini", callback_data=CALLBACK_REPORT_TODAY),
                InlineKeyboardButton("🗓 Minggu Ini", callback_data=CALLBACK_REPORT_WEEK),
            ],
            [InlineKeyboardButton("📆 Bulan Ini", callback_data=CALLBACK_REPORT_MONTH)],
            [
                InlineKeyboardButton(
                    "🗂 Kategori Pemasukan",
                    callback_data=CALLBACK_REPORT_INCOME_CATEGORIES,
                ),
                InlineKeyboardButton(
                    "🗂 Kategori Pengeluaran",
                    callback_data=CALLBACK_REPORT_EXPENSE_CATEGORIES,
                ),
            ],
            [InlineKeyboardButton("📈 Investasi", callback_data=CALLBACK_REPORT_INVESTMENT)],
        ]
    )
    return ReportMenuResponse(text="Pilih jenis laporan:", reply_markup=keyboard)


def build_category_report_response(
    transaction_type: str,
    *,
    connection: sqlite3.Connection,
    user_id: int,
    current_date: date,
) -> ReportMenuResponse:
    """Build current-month category totals for income or expense."""

    date_range = month_range(current_date)
    transactions = _transactions_for_range(connection, user_id=user_id, date_range=date_range)
    categories = _category_totals(
        transactions,
        category_names=_category_names_for(connection, user_id=user_id),
        transaction_type=transaction_type,
    )
    return ReportMenuResponse(
        text=format_category_report(
            title=f"Kategori {transaction_type_label(transaction_type)}",
            categories=categories,
        ),
        reply_markup=None,
    )


def build_investment_report_response(
    *,
    connection: sqlite3.Connection,
    user_id: int,
    current_date: date,
) -> ReportMenuResponse:
    """Build current-month investment report for one user."""

    date_range = month_range(current_date)
    transactions = _transactions_for_range(connection, user_id=user_id, date_range=date_range)
    summary = aggregate_transactions(
        transactions,
        category_names=_category_names_for(connection, user_id=user_id),
    )
    return ReportMenuResponse(text=format_investment_report(summary), reply_markup=None)


def _period_title_and_range(period: str, current_date: date) -> tuple[str, DateRange]:
    if period == "today":
        return "Laporan Harian", today_range(current_date)
    if period == "week":
        return "Laporan Mingguan", week_range(current_date)
    if period == "month":
        return "Laporan Bulanan", month_range(current_date)
    raise ValueError(f"Unknown report period: {period}")


def _transactions_for_range(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    date_range: DateRange,
) -> list[Transaction]:
    return list_transactions(
        connection,
        user_id=user_id,
        start_date=date_range.start_date.isoformat(),
        end_date=date_range.end_date.isoformat(),
    )


def _category_names_for(connection: sqlite3.Connection, *, user_id: int) -> dict[int, str]:
    rows = connection.execute(
        "SELECT id, name FROM categories WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def _category_totals(
    transactions: list[Transaction],
    *,
    category_names: dict[int, str],
    transaction_type: str,
) -> list[CategoryTotal]:
    totals: dict[str, int] = defaultdict(int)
    for transaction in transactions:
        if transaction.type != transaction_type:
            continue
        totals[category_names.get(transaction.category_id or 0, "Lainnya")] += transaction.amount

    return [
        CategoryTotal(name=name, amount=amount)
        for name, amount in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    ]
