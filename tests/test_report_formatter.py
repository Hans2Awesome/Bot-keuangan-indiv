"""Tests for Bot04 report text formatting."""

from __future__ import annotations

from datetime import date

from bot04.reports.aggregator import CategoryTotal, ReportSummary
from bot04.reports.date_ranges import DateRange
from bot04.reports.formatter import (
    format_category_report,
    format_investment_report,
    format_period_report,
)


def summary() -> ReportSummary:
    return ReportSummary(
        total_income=5_000_000,
        total_expense=100_000,
        total_investment=1_000_000,
        net=3_900_000,
        average_expense=50_000,
        top_expense_categories=[
            CategoryTotal(name="Transportasi", amount=75_000),
            CategoryTotal(name="Makan & Minum", amount=25_000),
        ],
        investment_percentage=20.0,
    )


def test_format_period_report_supports_daily_report() -> None:
    assert format_period_report(
        title="Laporan Harian",
        date_range=DateRange(date(2026, 5, 30), date(2026, 5, 30)),
        summary=summary(),
    ) == (
        "📊 Laporan Harian\n"
        "Periode: 30 Mei 2026\n\n"
        "Pemasukan: Rp5.000.000\n"
        "Pengeluaran: Rp100.000\n"
        "Investasi: Rp1.000.000\n"
        "Sisa Bersih: Rp3.900.000\n"
        "Rata-rata Pengeluaran: Rp50.000\n\n"
        "Top Pengeluaran:\n"
        "1. Transportasi — Rp75.000\n"
        "2. Makan & Minum — Rp25.000"
    )


def test_format_period_report_supports_weekly_or_monthly_date_range() -> None:
    report = format_period_report(
        title="Laporan Mingguan",
        date_range=DateRange(date(2026, 5, 25), date(2026, 5, 31)),
        summary=summary(),
    )

    assert report.startswith("📊 Laporan Mingguan\nPeriode: 25 Mei 2026 - 31 Mei 2026")


def test_format_period_report_shows_empty_category_message() -> None:
    empty_summary = ReportSummary(
        total_income=0,
        total_expense=0,
        total_investment=0,
        net=0,
        average_expense=0,
        top_expense_categories=[],
        investment_percentage=0.0,
    )

    report = format_period_report(
        title="Laporan Bulanan",
        date_range=DateRange(date(2026, 5, 1), date(2026, 5, 31)),
        summary=empty_summary,
    )

    assert "Top Pengeluaran:\n-" in report


def test_format_category_report_supports_income_and_expense_categories() -> None:
    categories = [
        CategoryTotal(name="Gaji", amount=5_000_000),
        CategoryTotal(name="Bonus", amount=100_000),
    ]

    assert format_category_report(title="Kategori Pemasukan", categories=categories) == (
        "🗂 Kategori Pemasukan\n"
        "1. Gaji — Rp5.000.000\n"
        "2. Bonus — Rp100.000"
    )


def test_format_category_report_handles_empty_categories() -> None:
    assert format_category_report(title="Kategori Pengeluaran", categories=[]) == (
        "🗂 Kategori Pengeluaran\n-"
    )


def test_format_investment_report_formats_investment_summary() -> None:
    assert format_investment_report(summary()) == (
        "📈 Laporan Investasi\n"
        "Total Investasi: Rp1.000.000\n"
        "Persentase dari Pemasukan: 20.00%"
    )
