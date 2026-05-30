"""Manual expense flow handler helpers for Bot04 Telegram bot."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import date

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot04.bot.handlers_quick_input import build_quick_confirmation_keyboard
from bot04.services.money_parser import MoneyParseError, parse_money
from bot04.services.pending_store import PendingConfirmationStore
from bot04.services.quick_input_parser import QuickInputResult
from bot04.services.transaction_preview import format_transaction_preview

CALLBACK_MANUAL_EXPENSE_START = "add_expense"
CALLBACK_MANUAL_EXPENSE_CATEGORY_PREFIX = "manual_expense_category:"
CALLBACK_MANUAL_EXPENSE_CANCEL = "manual_expense_cancel"

_AMOUNT_TOKEN_PATTERN = re.compile(
    r"(?i)(?:rp\s*)?\d+(?:[.,]\d+)*(?:(?:\s*(?:rb|ribu|jt|juta)\b)|(?:\s*k\b))?"
)


@dataclass(frozen=True)
class ManualExpenseResponse:
    """Telegram message/edit payload returned by manual expense flow logic."""

    text: str
    reply_markup: InlineKeyboardMarkup | None


def handle_manual_expense_callback(
    callback_data: str,
    *,
    connection: sqlite3.Connection,
    user_id: int,
    telegram_user_id: int,
    pending_store: PendingConfirmationStore,
) -> ManualExpenseResponse | None:
    """Handle manual expense category/cancel callbacks."""

    if callback_data == CALLBACK_MANUAL_EXPENSE_START:
        pending_store.clear(telegram_user_id=telegram_user_id)
        return ManualExpenseResponse(
            text="Pilih kategori pengeluaran:",
            reply_markup=_build_expense_category_keyboard(connection, user_id=user_id),
        )

    if callback_data == CALLBACK_MANUAL_EXPENSE_CANCEL:
        pending_store.clear(telegram_user_id=telegram_user_id)
        return ManualExpenseResponse(text="❌ Input pengeluaran dibatalkan.", reply_markup=None)

    if callback_data.startswith(CALLBACK_MANUAL_EXPENSE_CATEGORY_PREFIX):
        category_id = _parse_category_callback(callback_data)
        category_name = _expense_category_name(connection, user_id=user_id, category_id=category_id)
        if category_name is None:
            return ManualExpenseResponse(
                text="Kategori pengeluaran tidak ditemukan. Silakan mulai lagi dari menu.",
                reply_markup=None,
            )

        pending_store.set(
            telegram_user_id=telegram_user_id,
            preview=_expense_draft(category_name=category_name),
        )
        return ManualExpenseResponse(
            text=(
                f"Masukkan nominal pengeluaran untuk kategori {category_name}.\n"
                "Contoh: 25000 atau Rp25.000"
            ),
            reply_markup=None,
        )

    return None


def handle_manual_expense_amount_text(
    text: str,
    *,
    telegram_user_id: int,
    pending_store: PendingConfirmationStore,
    today: date | None = None,
) -> ManualExpenseResponse | None:
    """Read a nominal for the currently selected manual expense category."""

    draft = pending_store.get(telegram_user_id=telegram_user_id)
    if draft is None or draft.type != "expense" or draft.category_name is None or draft.amount is not None:
        return None

    try:
        amount = parse_money(text)
    except MoneyParseError:
        return ManualExpenseResponse(
            text="Nominal belum ditemukan. Masukkan nominal, contoh: 25000",
            reply_markup=None,
        )

    completed_preview = QuickInputResult(
        type="expense",
        category_name=draft.category_name,
        amount=amount,
        note=_build_note(text),
        asset_name=None,
        transaction_date=today or date.today(),
        confidence=1.0,
        needs_review=False,
        original_text=text.strip(),
        error=None,
    )
    pending_store.set(telegram_user_id=telegram_user_id, preview=completed_preview)
    return ManualExpenseResponse(
        text=format_transaction_preview(completed_preview),
        reply_markup=build_quick_confirmation_keyboard(),
    )


def _build_expense_category_keyboard(
    connection: sqlite3.Connection,
    *,
    user_id: int,
) -> InlineKeyboardMarkup:
    rows = connection.execute(
        """
        SELECT id, name
        FROM categories
        WHERE user_id = ? AND type = 'expense'
        ORDER BY id ASC
        """,
        (user_id,),
    ).fetchall()
    buttons = [
        InlineKeyboardButton(
            row[1],
            callback_data=f"{CALLBACK_MANUAL_EXPENSE_CATEGORY_PREFIX}{row[0]}",
        )
        for row in rows
    ]
    keyboard_rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    keyboard_rows.append(
        [InlineKeyboardButton("❌ Batal", callback_data=CALLBACK_MANUAL_EXPENSE_CANCEL)]
    )
    return InlineKeyboardMarkup(keyboard_rows)


def _parse_category_callback(callback_data: str) -> int:
    value = callback_data.removeprefix(CALLBACK_MANUAL_EXPENSE_CATEGORY_PREFIX)
    try:
        return int(value)
    except ValueError:
        return -1


def _expense_category_name(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    category_id: int,
) -> str | None:
    row = connection.execute(
        """
        SELECT name
        FROM categories
        WHERE user_id = ? AND id = ? AND type = 'expense'
        """,
        (user_id, category_id),
    ).fetchone()
    if row is None:
        return None
    return row[0]


def _expense_draft(*, category_name: str) -> QuickInputResult:
    return QuickInputResult(
        type="expense",
        category_name=category_name,
        amount=None,
        note="",
        asset_name=None,
        transaction_date=None,
        confidence=1.0,
        needs_review=False,
        original_text="",
        error=None,
    )


def _build_note(text: str) -> str:
    return " ".join(_AMOUNT_TOKEN_PATTERN.sub(" ", text, count=1).split())
