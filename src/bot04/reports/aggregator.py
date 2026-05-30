"""Aggregate transaction data for Bot04 reports."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from bot04.database.transactions import Transaction


@dataclass(frozen=True)
class CategoryTotal:
    """Total expense amount for one category."""

    name: str
    amount: int


@dataclass(frozen=True)
class ReportSummary:
    """Aggregated financial summary for a transaction list."""

    total_income: int
    total_expense: int
    total_investment: int
    net: int
    average_expense: int
    top_expense_categories: list[CategoryTotal]
    investment_percentage: float


def aggregate_transactions(
    transactions: list[Transaction],
    *,
    category_names: dict[int, str],
) -> ReportSummary:
    """Aggregate totals, net, expense categories, and investment percentage."""

    total_income = 0
    total_expense = 0
    total_investment = 0
    expense_count = 0
    expense_totals_by_category: dict[str, int] = defaultdict(int)

    for transaction in transactions:
        if transaction.type == "income":
            total_income += transaction.amount
        elif transaction.type == "expense":
            total_expense += transaction.amount
            expense_count += 1
            category_name = category_names.get(transaction.category_id or 0, "Lainnya")
            expense_totals_by_category[category_name] += transaction.amount
        elif transaction.type == "investment":
            total_investment += transaction.amount

    net = total_income - total_expense - total_investment
    average_expense = total_expense // expense_count if expense_count else 0
    investment_percentage = (
        round((total_investment / total_income) * 100, 2) if total_income > 0 else 0.0
    )

    top_expense_categories = [
        CategoryTotal(name=name, amount=amount)
        for name, amount in sorted(
            expense_totals_by_category.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]

    return ReportSummary(
        total_income=total_income,
        total_expense=total_expense,
        total_investment=total_investment,
        net=net,
        average_expense=average_expense,
        top_expense_categories=top_expense_categories,
        investment_percentage=investment_percentage,
    )
