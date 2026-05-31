"""Tests for README setup instructions."""

from __future__ import annotations

from pathlib import Path


def test_readme_contains_setup_run_and_test_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "cp .env.example .env" in readme
    assert "BOT_TOKEN" in readme
    assert "python -m bot04.main" in readme
    assert "pytest" in readme


def test_readme_mentions_dry_run_and_quick_input_examples() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "python -m bot04.main --dry-run" in readme
    assert "makan 25000" in readme
    assert "kopi 25k kemarin" in readme
    assert "invest btc 100000 dca mingguan" in readme


def test_readme_documents_transaction_history_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "/riwayat_pemasukan" in readme
    assert "/riwayat_pengeluaran" in readme
    assert "10 data per halaman" in readme
    assert "terbaru dulu" in readme
