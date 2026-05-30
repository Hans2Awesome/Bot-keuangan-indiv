"""Category repository and seeders for Bot04."""

from __future__ import annotations

import sqlite3

from bot04.domain import TransactionType

DEFAULT_CATEGORIES: tuple[tuple[TransactionType, str, str], ...] = (
    (TransactionType.INCOME, "Gaji", "gaji,salary"),
    (TransactionType.INCOME, "Bonus", "bonus"),
    (TransactionType.INCOME, "Freelance", "freelance,project"),
    (TransactionType.INCOME, "Bisnis", "bisnis,jualan,usaha"),
    (TransactionType.INCOME, "Hadiah", "hadiah,gift"),
    (TransactionType.INCOME, "Lainnya", "lainnya,lain"),
    (
        TransactionType.EXPENSE,
        "Makan & Minum",
        "makan,minum,kopi,sarapan,makan siang,makan malam",
    ),
    (
        TransactionType.EXPENSE,
        "Transportasi",
        "transport,transportasi,gojek,grab,bensin,parkir",
    ),
    (TransactionType.EXPENSE, "Belanja", "belanja,shopping,beli"),
    (TransactionType.EXPENSE, "Tagihan", "tagihan,listrik,air,internet,pulsa"),
    (TransactionType.EXPENSE, "Hiburan", "hiburan,nonton,game"),
    (TransactionType.EXPENSE, "Kesehatan", "kesehatan,dokter,obat"),
    (TransactionType.EXPENSE, "Pendidikan", "pendidikan,sekolah,kursus,buku"),
    (TransactionType.EXPENSE, "Lainnya", "lainnya,lain"),
    (TransactionType.INVESTMENT, "Saham", "saham,stock,bbca,bmri"),
    (
        TransactionType.INVESTMENT,
        "Crypto",
        "crypto,kripto,btc,eth,bitcoin,ethereum",
    ),
    (TransactionType.INVESTMENT, "Reksadana", "reksadana,rd"),
    (TransactionType.INVESTMENT, "Emas", "emas,gold,antam"),
    (TransactionType.INVESTMENT, "Deposito", "deposito"),
    (TransactionType.INVESTMENT, "Lainnya", "investasi,lainnya,lain"),
)


def seed_default_categories(connection: sqlite3.Connection, user_id: int) -> None:
    """Seed all default categories for one user without creating duplicates."""

    connection.executemany(
        """
        INSERT OR IGNORE INTO categories (user_id, type, name, aliases, is_default)
        VALUES (?, ?, ?, ?, 1)
        """,
        [
            (user_id, transaction_type.value, name, aliases)
            for transaction_type, name, aliases in DEFAULT_CATEGORIES
        ],
    )
    connection.commit()
