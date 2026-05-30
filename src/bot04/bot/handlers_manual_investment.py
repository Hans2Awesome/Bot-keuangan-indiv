"""Manual investment flow handler helpers for Bot04 Telegram bot."""

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

CALLBACK_MANUAL_INVESTMENT_START = "add_investment"
CALLBACK_MANUAL_INVESTMENT_CATEGORY_PREFIX = "manual_investment_category:"
CALLBACK_MANUAL_INVESTMENT_CANCEL = "manual_investment_cancel"

_AMOUNT_TOKEN_PATTERN = re.compile(
    r"(?i)(?:rp\s*)?\d+(?:[.,]\d+)*(?:(?:\s*(?:rb|ribu|jt|juta)\b)|(?:\s*k\b))?"
)
_ASSET_ALIASES: dict[str, list[str]] = {
    "BTC": ["btc", "bitcoin"],
    "ETH": ["eth", "ethereum"],
    "Emas": ["emas", "gold", "antam"],
}


@dataclass(frozen=True)
class ManualInvestmentResponse:
    """Telegram message/edit payload returned by manual investment flow logic."""

    text: str
    reply_markup: InlineKeyboardMarkup | None


def handle_manual_investment_callback(
    callback_data: str,
    *,
    connection: sqlite3.Connection,
    user_id: int,
    telegram_user_id: int,
    pending_store: PendingConfirmationStore,
) -> ManualInvestmentResponse | None:
    """Handle manual investment category/cancel callbacks."""

    if callback_data == CALLBACK_MANUAL_INVESTMENT_START:
        pending_store.clear(telegram_user_id=telegram_user_id)
        return ManualInvestmentResponse(
            text="Pilih jenis investasi:",
            reply_markup=_build_investment_category_keyboard(connection, user_id=user_id),
        )

    if callback_data == CALLBACK_MANUAL_INVESTMENT_CANCEL:
        pending_store.clear(telegram_user_id=telegram_user_id)
        return ManualInvestmentResponse(text="❌ Input investasi dibatalkan.", reply_markup=None)

    if callback_data.startswith(CALLBACK_MANUAL_INVESTMENT_CATEGORY_PREFIX):
        category_id = _parse_category_callback(callback_data)
        category_name = _investment_category_name(connection, user_id=user_id, category_id=category_id)
        if category_name is None:
            return ManualInvestmentResponse(
                text="Kategori investasi tidak ditemukan. Silakan mulai lagi dari menu.",
                reply_markup=None,
            )

        pending_store.set(
            telegram_user_id=telegram_user_id,
            preview=_investment_draft(category_name=category_name),
        )
        return ManualInvestmentResponse(
            text=(
                f"Masukkan nominal investasi untuk kategori {category_name}.\n"
                "Contoh: 100000 atau Rp100.000"
            ),
            reply_markup=None,
        )

    return None


def handle_manual_investment_amount_text(
    text: str,
    *,
    telegram_user_id: int,
    pending_store: PendingConfirmationStore,
    today: date | None = None,
) -> ManualInvestmentResponse | None:
    """Read a nominal for the currently selected manual investment category."""

    draft = pending_store.get(telegram_user_id=telegram_user_id)
    if draft is None or draft.type != "investment" or draft.category_name is None or draft.amount is not None:
        return None

    try:
        amount = parse_money(text)
    except MoneyParseError:
        return ManualInvestmentResponse(
            text="Nominal belum ditemukan. Masukkan nominal, contoh: 100000",
            reply_markup=None,
        )

    asset_name = _detect_asset_name(text, fallback=draft.asset_name)
    completed_preview = QuickInputResult(
        type="investment",
        category_name=draft.category_name,
        amount=amount,
        note=_build_note(text, asset_name=asset_name),
        asset_name=asset_name,
        transaction_date=today or date.today(),
        confidence=1.0,
        needs_review=False,
        original_text=text.strip(),
        error=None,
    )
    pending_store.set(telegram_user_id=telegram_user_id, preview=completed_preview)
    return ManualInvestmentResponse(
        text=format_transaction_preview(completed_preview),
        reply_markup=build_quick_confirmation_keyboard(),
    )


def _build_investment_category_keyboard(
    connection: sqlite3.Connection,
    *,
    user_id: int,
) -> InlineKeyboardMarkup:
    rows = connection.execute(
        """
        SELECT id, name
        FROM categories
        WHERE user_id = ? AND type = 'investment'
        ORDER BY id ASC
        """,
        (user_id,),
    ).fetchall()
    buttons = [
        InlineKeyboardButton(
            row[1],
            callback_data=f"{CALLBACK_MANUAL_INVESTMENT_CATEGORY_PREFIX}{row[0]}",
        )
        for row in rows
    ]
    keyboard_rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    keyboard_rows.append(
        [InlineKeyboardButton("❌ Batal", callback_data=CALLBACK_MANUAL_INVESTMENT_CANCEL)]
    )
    return InlineKeyboardMarkup(keyboard_rows)


def _parse_category_callback(callback_data: str) -> int:
    value = callback_data.removeprefix(CALLBACK_MANUAL_INVESTMENT_CATEGORY_PREFIX)
    try:
        return int(value)
    except ValueError:
        return -1


def _investment_category_name(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    category_id: int,
) -> str | None:
    row = connection.execute(
        """
        SELECT name
        FROM categories
        WHERE user_id = ? AND id = ? AND type = 'investment'
        """,
        (user_id, category_id),
    ).fetchone()
    if row is None:
        return None
    return row[0]


def _investment_draft(*, category_name: str) -> QuickInputResult:
    return QuickInputResult(
        type="investment",
        category_name=category_name,
        amount=None,
        note="",
        asset_name=_default_asset_name(category_name),
        transaction_date=None,
        confidence=1.0,
        needs_review=False,
        original_text="",
        error=None,
    )


def _default_asset_name(category_name: str) -> str | None:
    if category_name == "Crypto":
        return "Crypto"
    if category_name == "Emas":
        return "Emas"
    return None


def _detect_asset_name(text: str, *, fallback: str | None) -> str | None:
    lowered = text.lower()
    for asset_name, aliases in _ASSET_ALIASES.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", lowered):
                return asset_name
    return fallback


def _build_note(text: str, *, asset_name: str | None) -> str:
    cleaned = _AMOUNT_TOKEN_PATTERN.sub(" ", text, count=1)
    if asset_name in _ASSET_ALIASES:
        for alias in _ASSET_ALIASES[asset_name]:
            cleaned = re.sub(rf"(?i)\b{re.escape(alias)}\b", " ", cleaned)
    return " ".join(cleaned.split())
