"""Telegram application wiring for Bot04."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    BaseHandler,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot04.bot.handlers_confirm import handle_quick_confirm_callback
from bot04.bot.help_text import build_help_text
from bot04.bot.handlers_manual_expense import (
    CALLBACK_MANUAL_EXPENSE_CANCEL,
    CALLBACK_MANUAL_EXPENSE_CATEGORY_PREFIX,
    CALLBACK_MANUAL_EXPENSE_START,
    handle_manual_expense_amount_text,
    handle_manual_expense_callback,
)
from bot04.bot.handlers_manual_income import (
    CALLBACK_MANUAL_INCOME_CANCEL,
    CALLBACK_MANUAL_INCOME_CATEGORY_PREFIX,
    CALLBACK_MANUAL_INCOME_START,
    handle_manual_income_amount_text,
    handle_manual_income_callback,
)
from bot04.bot.handlers_manual_investment import (
    CALLBACK_MANUAL_INVESTMENT_CANCEL,
    CALLBACK_MANUAL_INVESTMENT_CATEGORY_PREFIX,
    CALLBACK_MANUAL_INVESTMENT_START,
    handle_manual_investment_amount_text,
    handle_manual_investment_callback,
)
from bot04.bot.handlers_quick_input import (
    CALLBACK_QUICK_CANCEL,
    CALLBACK_QUICK_SAVE,
    handle_quick_input_text,
)
from bot04.bot.handlers_reports import (
    CALLBACK_REPORT_EXPENSE_CATEGORIES,
    CALLBACK_REPORT_INCOME_CATEGORIES,
    CALLBACK_REPORT_INVESTMENT,
    CALLBACK_REPORT_MONTH,
    CALLBACK_REPORT_TODAY,
    CALLBACK_REPORT_WEEK,
    build_category_report_response,
    build_investment_report_response,
    build_period_report_response,
    build_report_menu_response,
)
from bot04.bot.handlers_start import build_start_response, register_start_user
from bot04.bot.handlers_transactions import (
    CALLBACK_TRANSACTION_DELETE_CANCEL,
    CALLBACK_TRANSACTION_DELETE_CONFIRM_PREFIX,
    CALLBACK_TRANSACTION_DELETE_PREFIX,
    CALLBACK_TRANSACTION_EDIT_PREFIX,
    CALLBACK_TRANSACTIONS_RECENT,
    handle_transaction_edit_text,
    handle_transactions_callback,
)
from bot04.config import Config
from bot04.database.connection import connect
from bot04.database.schema import init_db
from bot04.services.pending_store import PendingConfirmationStore


@dataclass(frozen=True)
class BotDependencies:
    """Runtime dependencies shared by Telegram handlers."""

    connection: sqlite3.Connection
    pending_store: PendingConfirmationStore


def build_application(
    *,
    config: Config,
    dependencies: BotDependencies | None = None,
) -> Application:
    """Build a python-telegram-bot Application and register all Bot04 handlers."""

    dependencies = dependencies or build_dependencies(config.database_path)
    application = ApplicationBuilder().token(config.bot_token).build()
    application.bot_data["connection"] = dependencies.connection
    application.bot_data["pending_store"] = dependencies.pending_store

    for handler in build_handlers(dependencies):
        application.add_handler(handler)

    return application


def build_dependencies(database_path: str) -> BotDependencies:
    """Create SQLite and pending-store dependencies for the bot runtime."""

    connection = connect(database_path)
    init_db(connection)
    return BotDependencies(
        connection=connection,
        pending_store=PendingConfirmationStore(),
    )


def build_handlers(dependencies: BotDependencies) -> list[BaseHandler]:
    """Build command, callback, and message handlers for the Telegram app."""

    # ``dependencies`` is accepted so tests can verify wiring without relying on
    # global state; PTB callbacks read the same objects from application.bot_data.
    _ = dependencies
    return [
        CommandHandler("start", _start_or_menu_command),
        CommandHandler("menu", _start_or_menu_command),
        CommandHandler("today", _today_command),
        CommandHandler("week", _week_command),
        CommandHandler("month", _month_command),
        CommandHandler("report", _report_command),
        CommandHandler("help", _help_command),
        CallbackQueryHandler(
            _quick_confirm_callback,
            pattern=f"^({CALLBACK_QUICK_SAVE}|{CALLBACK_QUICK_CANCEL})$",
        ),
        CallbackQueryHandler(
            _manual_income_callback,
            pattern=(
                f"^({CALLBACK_MANUAL_INCOME_START}|{CALLBACK_MANUAL_INCOME_CANCEL}|"
                f"{CALLBACK_MANUAL_INCOME_CATEGORY_PREFIX}\\d+)$"
            ),
        ),
        CallbackQueryHandler(
            _manual_expense_callback,
            pattern=(
                f"^({CALLBACK_MANUAL_EXPENSE_START}|{CALLBACK_MANUAL_EXPENSE_CANCEL}|"
                f"{CALLBACK_MANUAL_EXPENSE_CATEGORY_PREFIX}\\d+)$"
            ),
        ),
        CallbackQueryHandler(
            _manual_investment_callback,
            pattern=(
                f"^({CALLBACK_MANUAL_INVESTMENT_START}|{CALLBACK_MANUAL_INVESTMENT_CANCEL}|"
                f"{CALLBACK_MANUAL_INVESTMENT_CATEGORY_PREFIX}\\d+)$"
            ),
        ),
        CallbackQueryHandler(
            _transactions_callback,
            pattern=(
                f"^({CALLBACK_TRANSACTIONS_RECENT}|{CALLBACK_TRANSACTION_DELETE_CANCEL}|"
                f"{CALLBACK_TRANSACTION_EDIT_PREFIX}\\d+|{CALLBACK_TRANSACTION_DELETE_PREFIX}\\d+|"
                f"{CALLBACK_TRANSACTION_DELETE_CONFIRM_PREFIX}\\d+)$"
            ),
        ),
        CallbackQueryHandler(
            _report_callback,
            pattern=(
                f"^({CALLBACK_REPORT_TODAY}|{CALLBACK_REPORT_WEEK}|{CALLBACK_REPORT_MONTH}|"
                f"{CALLBACK_REPORT_INCOME_CATEGORIES}|{CALLBACK_REPORT_EXPENSE_CATEGORIES}|"
                f"{CALLBACK_REPORT_INVESTMENT})$"
            ),
        ),
        MessageHandler(filters.TEXT & ~filters.COMMAND, _quick_input_message),
    ]


async def _start_or_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.effective_message is None:
        return

    connection = _connection(context)
    register_start_user(
        connection,
        telegram_user_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )
    text, reply_markup = build_start_response(user.first_name)
    await update.effective_message.reply_text(text, reply_markup=reply_markup)


async def _quick_input_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None or message.text is None:
        return

    manual_income_response = handle_manual_income_amount_text(
        message.text,
        telegram_user_id=user.id,
        pending_store=_pending_store(context),
    )
    if manual_income_response is not None:
        await message.reply_text(manual_income_response.text, reply_markup=manual_income_response.reply_markup)
        return

    manual_expense_response = handle_manual_expense_amount_text(
        message.text,
        telegram_user_id=user.id,
        pending_store=_pending_store(context),
    )
    if manual_expense_response is not None:
        await message.reply_text(manual_expense_response.text, reply_markup=manual_expense_response.reply_markup)
        return

    manual_investment_response = handle_manual_investment_amount_text(
        message.text,
        telegram_user_id=user.id,
        pending_store=_pending_store(context),
    )
    if manual_investment_response is not None:
        await message.reply_text(
            manual_investment_response.text,
            reply_markup=manual_investment_response.reply_markup,
        )
        return

    db_user = register_start_user(
        _connection(context),
        telegram_user_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )
    transaction_edit_response = handle_transaction_edit_text(
        message.text,
        connection=_connection(context),
        user_id=db_user.id,
        telegram_user_id=user.id,
        pending_store=_pending_store(context),
    )
    if transaction_edit_response is not None:
        await message.reply_text(
            transaction_edit_response.text,
            reply_markup=transaction_edit_response.reply_markup,
        )
        return

    response = handle_quick_input_text(
        message.text,
        telegram_user_id=user.id,
        pending_store=_pending_store(context),
    )
    if response is None:
        return
    await message.reply_text(response.text, reply_markup=response.reply_markup)


async def _manual_income_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None or query.data is None:
        return

    await query.answer()
    db_user = register_start_user(
        _connection(context),
        telegram_user_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )
    response = handle_manual_income_callback(
        query.data,
        connection=_connection(context),
        user_id=db_user.id,
        telegram_user_id=user.id,
        pending_store=_pending_store(context),
    )
    if response is None:
        return
    await query.edit_message_text(text=response.text, reply_markup=response.reply_markup)


async def _manual_expense_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None or query.data is None:
        return

    await query.answer()
    db_user = register_start_user(
        _connection(context),
        telegram_user_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )
    response = handle_manual_expense_callback(
        query.data,
        connection=_connection(context),
        user_id=db_user.id,
        telegram_user_id=user.id,
        pending_store=_pending_store(context),
    )
    if response is None:
        return
    await query.edit_message_text(text=response.text, reply_markup=response.reply_markup)


async def _manual_investment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None or query.data is None:
        return

    await query.answer()
    db_user = register_start_user(
        _connection(context),
        telegram_user_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )
    response = handle_manual_investment_callback(
        query.data,
        connection=_connection(context),
        user_id=db_user.id,
        telegram_user_id=user.id,
        pending_store=_pending_store(context),
    )
    if response is None:
        return
    await query.edit_message_text(text=response.text, reply_markup=response.reply_markup)


async def _transactions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None or query.data is None:
        return

    await query.answer()
    db_user = register_start_user(
        _connection(context),
        telegram_user_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )
    response = handle_transactions_callback(
        query.data,
        connection=_connection(context),
        user_id=db_user.id,
        telegram_user_id=user.id,
        pending_store=_pending_store(context),
    )
    if response is None:
        return
    await query.edit_message_text(text=response.text, reply_markup=response.reply_markup)


async def _quick_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None or query.data is None:
        return

    await query.answer()
    db_user = register_start_user(
        _connection(context),
        telegram_user_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )
    response = handle_quick_confirm_callback(
        query.data,
        connection=_connection(context),
        user_id=db_user.id,
        telegram_user_id=user.id,
        pending_store=_pending_store(context),
    )
    if response is None:
        return
    await query.edit_message_text(text=response.text, reply_markup=response.reply_markup)


async def _today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_period_report(update, context, "today")


async def _week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_period_report(update, context, "week")


async def _month_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_period_report(update, context, "month")


async def _report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    response = build_report_menu_response()
    await update.effective_message.reply_text(response.text, reply_markup=response.reply_markup)


async def _help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(build_help_text())


async def _report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None or query.data is None:
        return

    await query.answer()
    db_user = register_start_user(
        _connection(context),
        telegram_user_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )
    today = date.today()

    if query.data == CALLBACK_REPORT_TODAY:
        response = build_period_report_response(
            "today", connection=_connection(context), user_id=db_user.id, current_date=today
        )
    elif query.data == CALLBACK_REPORT_WEEK:
        response = build_period_report_response(
            "week", connection=_connection(context), user_id=db_user.id, current_date=today
        )
    elif query.data == CALLBACK_REPORT_MONTH:
        response = build_period_report_response(
            "month", connection=_connection(context), user_id=db_user.id, current_date=today
        )
    elif query.data == CALLBACK_REPORT_INCOME_CATEGORIES:
        response = build_category_report_response(
            "income", connection=_connection(context), user_id=db_user.id, current_date=today
        )
    elif query.data == CALLBACK_REPORT_EXPENSE_CATEGORIES:
        response = build_category_report_response(
            "expense", connection=_connection(context), user_id=db_user.id, current_date=today
        )
    else:
        response = build_investment_report_response(
            connection=_connection(context), user_id=db_user.id, current_date=today
        )

    await query.edit_message_text(text=response.text, reply_markup=response.reply_markup)


async def _send_period_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    period: str,
) -> None:
    user = update.effective_user
    if user is None or update.effective_message is None:
        return

    db_user = register_start_user(
        _connection(context),
        telegram_user_id=user.id,
        first_name=user.first_name,
        username=user.username,
    )
    response = build_period_report_response(
        period,
        connection=_connection(context),
        user_id=db_user.id,
        current_date=date.today(),
    )
    await update.effective_message.reply_text(response.text, reply_markup=response.reply_markup)


def _connection(context: ContextTypes.DEFAULT_TYPE) -> sqlite3.Connection:
    return context.application.bot_data["connection"]


def _pending_store(context: ContextTypes.DEFAULT_TYPE) -> PendingConfirmationStore:
    return context.application.bot_data["pending_store"]
