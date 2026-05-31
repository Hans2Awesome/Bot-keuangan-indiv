# Report Transaction Log Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Tambahkan command dan tombol di `/report` untuk melihat riwayat pemasukan dan riwayat pengeluaran, masing-masing 10 transaksi per halaman, diurutkan dari waktu terbaru.

**Architecture:** Fitur dibuat sebagai bagian dari report layer yang sudah ada. Query transaksi tetap user-scoped, formatter riwayat dibuat terpisah agar format Telegram konsisten, lalu handler `/report` menambahkan tombol dan callback pagination.

**Tech Stack:** Python, SQLite, python-telegram-bot, pytest.

---

## Format UX yang Diinginkan

### Command menu Telegram

Tambahkan command:

- `/riwayat_pemasukan` — `💰 Riwayat Pemasukan`
- `/riwayat_pengeluaran` — `💸 Riwayat Pengeluaran`

Command lama tetap ada:

- `/start`
- `/menu`
- `/help`
- `/today`
- `/week`
- `/month`
- `/report`

### Tombol di `/report`

Menu `/report` menjadi:

```text
Pilih jenis laporan:
```

Keyboard:

```text
[📅 Hari Ini] [🗓 Minggu Ini]
[📆 Bulan Ini]
[🗂 Kategori Pemasukan] [🗂 Kategori Pengeluaran]
[💰 Riwayat Pemasukan] [💸 Riwayat Pengeluaran]
[📈 Investasi]
```

### Format riwayat pemasukan

Contoh halaman pertama:

```text
💰 Riwayat Pemasukan
Halaman 1 dari 3
Urutan: terbaru dulu

1. 31 Mei 2026 — Rp5.000.000
   Kategori: Gaji
   Catatan: gaji bulanan

2. 30 Mei 2026 — Rp150.000
   Kategori: Bonus
   Catatan: bonus proyek

...

10. 20 Mei 2026 — Rp75.000
    Kategori: Hadiah
    Catatan: -
```

Keyboard pagination:

```text
[⬅️ Sebelumnya] [➡️ Berikutnya]
[🔙 Kembali ke Report]
```

Jika halaman pertama, tombol `⬅️ Sebelumnya` tidak ditampilkan. Jika halaman terakhir, tombol `➡️ Berikutnya` tidak ditampilkan.

### Format riwayat pengeluaran

Contoh:

```text
💸 Riwayat Pengeluaran
Halaman 1 dari 2
Urutan: terbaru dulu

1. 31 Mei 2026 — Rp25.000
   Kategori: Makan & Minum
   Catatan: makan siang

2. 31 Mei 2026 — Rp15.000
   Kategori: Transportasi
   Catatan: gojek kantor
```

### Empty state

Jika belum ada log:

```text
Belum ada riwayat pemasukan.
```

atau:

```text
Belum ada riwayat pengeluaran.
```

Keyboard:

```text
[🔙 Kembali ke Report]
```

### Pagination rules

- 10 riwayat per halaman.
- Sort: `transaction_date DESC, id DESC`.
- Page callback memakai 1-based page number.
- User hanya bisa melihat transaksi miliknya sendiri.
- Hanya tipe `income` untuk riwayat pemasukan.
- Hanya tipe `expense` untuk riwayat pengeluaran.
- Investasi tidak masuk ke dua log ini.

---

## Task 1: Tambahkan repository query untuk riwayat transaksi per tipe

**Objective:** Buat fungsi database yang mengambil transaksi user berdasarkan tipe dengan pagination dan total count.

**Files:**
- Modify: `src/bot04/database/transactions.py`
- Test: `tests/test_transactions_repository.py`

**Step 1: Write failing tests**

Tambahkan test untuk:

- `list_transactions_by_type(...)` hanya mengembalikan transaksi milik user.
- Filter tipe `income` tidak menyertakan `expense`/`investment`.
- Urutan `transaction_date DESC, id DESC`.
- `limit=10`, `offset=10` mengembalikan halaman kedua.
- `count_transactions_by_type(...)` menghitung total matching transaksi.

Contoh API target:

```python
transactions = list_transactions_by_type(
    connection,
    user_id=user_id,
    transaction_type="income",
    limit=10,
    offset=0,
)

total = count_transactions_by_type(
    connection,
    user_id=user_id,
    transaction_type="income",
)
```

**Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_transactions_repository.py -q
```

Expected: FAIL karena fungsi belum ada.

**Step 3: Implement minimal code**

Tambahkan di `src/bot04/database/transactions.py`:

```python
def list_transactions_by_type(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    transaction_type: str,
    limit: int,
    offset: int,
) -> list[Transaction]:
    _configure_rows(connection)
    rows = connection.execute(
        """
        SELECT id, user_id, type, category_id, amount, note, asset_name, transaction_date
        FROM transactions
        WHERE user_id = ? AND type = ?
        ORDER BY transaction_date DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        (user_id, transaction_type, limit, offset),
    ).fetchall()
    return [_row_to_transaction(row) for row in rows]


def count_transactions_by_type(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    transaction_type: str,
) -> int:
    row = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM transactions
        WHERE user_id = ? AND type = ?
        """,
        (user_id, transaction_type),
    ).fetchone()
    return int(row[0])
```

**Step 4: Verify**

```bash
python -m pytest tests/test_transactions_repository.py -q
```

Expected: PASS.

---

## Task 2: Buat formatter riwayat transaksi

**Objective:** Format 10 transaksi per halaman menjadi teks Telegram yang rapi.

**Files:**
- Modify: `src/bot04/reports/formatter.py`
- Test: `tests/test_report_formatter.py`

**Step 1: Write failing tests**

Tambahkan test untuk:

- `format_transaction_log_report(...)` pemasukan menampilkan judul `💰 Riwayat Pemasukan`.
- Pengeluaran menampilkan judul `💸 Riwayat Pengeluaran`.
- Menampilkan `Halaman X dari Y`.
- Tanggal memakai format Indonesia (`31 Mei 2026`).
- Amount memakai Rupiah (`Rp25.000`).
- Kategori fallback `Lainnya` jika `category_id` tidak ada.
- Note kosong menjadi `-`.
- Empty state sesuai tipe.

Target API:

```python
text = format_transaction_log_report(
    transaction_type="income",
    transactions=transactions,
    category_names={1: "Gaji"},
    page=1,
    total_pages=3,
)
```

**Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_report_formatter.py -q
```

Expected: FAIL karena formatter belum ada.

**Step 3: Implement formatter**

Tambahkan helper publik:

```python
def format_transaction_log_report(
    *,
    transaction_type: str,
    transactions: list[Transaction],
    category_names: dict[int, str],
    page: int,
    total_pages: int,
) -> str:
    if not transactions:
        label = "pemasukan" if transaction_type == "income" else "pengeluaran"
        return f"Belum ada riwayat {label}."

    icon_title = "💰 Riwayat Pemasukan" if transaction_type == "income" else "💸 Riwayat Pengeluaran"
    lines = [
        icon_title,
        f"Halaman {page} dari {total_pages}",
        "Urutan: terbaru dulu",
        "",
    ]
    for index, transaction in enumerate(transactions, start=1):
        category_name = category_names.get(transaction.category_id or 0, "Lainnya")
        lines.extend(
            [
                f"{index}. {_format_transaction_date(transaction.transaction_date)} — {_format_rupiah(transaction.amount)}",
                f"   Kategori: {category_name}",
                f"   Catatan: {transaction.note or '-'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()
```

Tambahkan `_format_transaction_date(value: str)` yang parse `YYYY-MM-DD` lalu pakai `_format_indonesian_date`.

**Step 4: Verify**

```bash
python -m pytest tests/test_report_formatter.py -q
```

Expected: PASS.

---

## Task 3: Buat report riwayat response dan tombol pagination

**Objective:** Tambahkan builder response untuk riwayat pemasukan/pengeluaran dan keyboard pagination.

**Files:**
- Modify: `src/bot04/bot/handlers_reports.py`
- Test: `tests/test_handlers_reports.py`

**Step 1: Write failing tests**

Tambahkan test untuk:

- `/report` menu punya tombol `💰 Riwayat Pemasukan` dan `💸 Riwayat Pengeluaran`.
- `build_transaction_log_response("income", page=1, ...)` mengambil 10 transaksi terbaru.
- Halaman 1 dari 2 hanya menampilkan tombol `➡️ Berikutnya` dan `🔙 Kembali ke Report`.
- Halaman 2 dari 2 menampilkan tombol `⬅️ Sebelumnya` dan `🔙 Kembali ke Report`.
- Empty state tetap punya tombol `🔙 Kembali ke Report`.
- Page kurang dari 1 dinormalisasi ke 1.
- Page lebih dari total halaman dinormalisasi ke halaman terakhir.

Callback constants target:

```python
CALLBACK_REPORT_INCOME_LOG_PREFIX = "report_income_log:"
CALLBACK_REPORT_EXPENSE_LOG_PREFIX = "report_expense_log:"
CALLBACK_REPORT_BACK_TO_MENU = "report_menu"
```

**Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_handlers_reports.py -q
```

Expected: FAIL karena constants/builder belum ada.

**Step 3: Implement response builder**

Tambahkan di `handlers_reports.py`:

```python
LOG_PAGE_SIZE = 10
CALLBACK_REPORT_INCOME_LOG_PREFIX = "report_income_log:"
CALLBACK_REPORT_EXPENSE_LOG_PREFIX = "report_expense_log:"
CALLBACK_REPORT_BACK_TO_MENU = "report_menu"
```

Tambahkan tombol di `build_report_menu_response()`:

```python
[
    InlineKeyboardButton("💰 Riwayat Pemasukan", callback_data=f"{CALLBACK_REPORT_INCOME_LOG_PREFIX}1"),
    InlineKeyboardButton("💸 Riwayat Pengeluaran", callback_data=f"{CALLBACK_REPORT_EXPENSE_LOG_PREFIX}1"),
],
```

Tambahkan builder:

```python
def build_transaction_log_response(
    transaction_type: str,
    *,
    connection: sqlite3.Connection,
    user_id: int,
    page: int,
) -> ReportMenuResponse:
    total = count_transactions_by_type(connection, user_id=user_id, transaction_type=transaction_type)
    total_pages = max(1, math.ceil(total / LOG_PAGE_SIZE))
    page = min(max(page, 1), total_pages)
    offset = (page - 1) * LOG_PAGE_SIZE
    transactions = list_transactions_by_type(
        connection,
        user_id=user_id,
        transaction_type=transaction_type,
        limit=LOG_PAGE_SIZE,
        offset=offset,
    )
    prefix = CALLBACK_REPORT_INCOME_LOG_PREFIX if transaction_type == "income" else CALLBACK_REPORT_EXPENSE_LOG_PREFIX
    return ReportMenuResponse(
        text=format_transaction_log_report(
            transaction_type=transaction_type,
            transactions=transactions,
            category_names=_category_names_for(connection, user_id=user_id),
            page=page,
            total_pages=total_pages,
        ),
        reply_markup=_log_pagination_keyboard(prefix=prefix, page=page, total_pages=total_pages),
    )
```

**Step 4: Verify**

```bash
python -m pytest tests/test_handlers_reports.py -q
```

Expected: PASS.

---

## Task 4: Wire command `/riwayat_pemasukan` dan `/riwayat_pengeluaran`

**Objective:** Command langsung membuka riwayat pemasukan/pengeluaran halaman 1.

**Files:**
- Modify: `src/bot04/bot/app.py`
- Modify: `tests/test_bot_app.py`
- Modify: `tests/test_bot_commands.py`

**Step 1: Write failing tests**

Tambahkan test untuk:

- `BOT_COMMANDS` berisi `riwayat_pemasukan` dan `riwayat_pengeluaran`.
- `build_handlers(...)` register `CommandHandler("riwayat_pemasukan", ...)`.
- `build_handlers(...)` register `CommandHandler("riwayat_pengeluaran", ...)`.
- Callback pattern report mencakup prefix pagination riwayat.

Expected command list:

```python
("riwayat_pemasukan", "💰 Riwayat Pemasukan")
("riwayat_pengeluaran", "💸 Riwayat Pengeluaran")
```

**Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_bot_app.py tests/test_bot_commands.py -q
```

Expected: FAIL.

**Step 3: Implement app wiring**

Di `BOT_COMMANDS`, tambahkan:

```python
BotCommand("riwayat_pemasukan", "💰 Riwayat Pemasukan"),
BotCommand("riwayat_pengeluaran", "💸 Riwayat Pengeluaran"),
```

Di `build_handlers(...)`, tambahkan:

```python
CommandHandler("riwayat_pemasukan", _riwayat_pemasukan_command),
CommandHandler("riwayat_pengeluaran", _riwayat_pengeluaran_command),
```

Tambahkan async command handler:

```python
async def _riwayat_pemasukan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_transaction_log(update, context, "income", page=1)

async def _riwayat_pengeluaran_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_transaction_log(update, context, "expense", page=1)
```

Tambahkan helper `_send_transaction_log(...)` yang register user lalu panggil `build_transaction_log_response(...)`.

**Step 4: Verify**

```bash
python -m pytest tests/test_bot_app.py tests/test_bot_commands.py -q
```

Expected: PASS.

---

## Task 5: Wire callback pagination di `/report`

**Objective:** Tombol riwayat dan pagination bekerja dari menu `/report` tanpa mengirim pesan baru.

**Files:**
- Modify: `src/bot04/bot/app.py`
- Test: `tests/test_bot_app.py`
- Test: `tests/test_handlers_reports.py`

**Step 1: Write failing tests**

Tambahkan test pattern callback untuk:

- `report_income_log:1`
- `report_income_log:2`
- `report_expense_log:1`
- `report_expense_log:2`
- `report_menu`

Tambahkan test behavior helper parser callback jika dibuat.

**Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_bot_app.py tests/test_handlers_reports.py -q
```

Expected: FAIL.

**Step 3: Implement callback handling**

Update callback pattern report agar mencakup:

```python
f"{CALLBACK_REPORT_INCOME_LOG_PREFIX}\\d+|"
f"{CALLBACK_REPORT_EXPENSE_LOG_PREFIX}\\d+|"
f"{CALLBACK_REPORT_BACK_TO_MENU}"
```

Update `_report_callback(...)`:

```python
elif query.data == CALLBACK_REPORT_BACK_TO_MENU:
    response = build_report_menu_response()
elif query.data.startswith(CALLBACK_REPORT_INCOME_LOG_PREFIX):
    response = build_transaction_log_response(
        "income",
        connection=_connection(context),
        user_id=db_user.id,
        page=_parse_report_page(query.data, CALLBACK_REPORT_INCOME_LOG_PREFIX),
    )
elif query.data.startswith(CALLBACK_REPORT_EXPENSE_LOG_PREFIX):
    response = build_transaction_log_response(
        "expense",
        connection=_connection(context),
        user_id=db_user.id,
        page=_parse_report_page(query.data, CALLBACK_REPORT_EXPENSE_LOG_PREFIX),
    )
```

**Step 4: Verify**

```bash
python -m pytest tests/test_bot_app.py tests/test_handlers_reports.py -q
```

Expected: PASS.

---

## Task 6: Update README/help jika perlu

**Objective:** Dokumentasikan command baru dan cara membaca log.

**Files:**
- Modify: `README.md`
- Modify: `src/bot04/bot/help_text.py`
- Test: `tests/test_readme.py`
- Test: `tests/test_help_text.py`

**Step 1: Write failing tests**

Tambahkan assertion bahwa README/help menyebut:

- `/riwayat_pemasukan`
- `/riwayat_pengeluaran`
- 10 riwayat per halaman
- urutan terbaru dulu

**Step 2: Run test to verify failure**

```bash
python -m pytest tests/test_readme.py tests/test_help_text.py -q
```

Expected: FAIL.

**Step 3: Update docs/help**

Tambahkan ringkasan command:

```text
/riwayat_pemasukan — melihat riwayat pemasukan, 10 data per halaman, terbaru dulu.
/riwayat_pengeluaran — melihat riwayat pengeluaran, 10 data per halaman, terbaru dulu.
```

**Step 4: Verify**

```bash
python -m pytest tests/test_readme.py tests/test_help_text.py -q
```

Expected: PASS.

---

## Task 7: Final verification dan restart bot

**Objective:** Pastikan semua test pass, dry-run aman, lalu restart bot agar command Telegram refresh.

**Files:**
- No code changes expected.

**Step 1: Run full tests**

```bash
python -m pytest -q
```

Expected: PASS semua test.

**Step 2: Run dry-run**

```bash
python -m bot04.main --dry-run
```

Expected:

```text
Bot04 configuration loaded: database_path=bot04.sqlite3, timezone=Asia/Jakarta, currency=IDR
```

**Step 3: Restart bot process**

Jika ada process lama, stop dulu. Lalu jalankan ulang dari `/root/projects/bot04`:

```bash
python -m bot04.main
```

**Step 4: Manual smoke test Telegram**

Cek:

1. Buka command menu Telegram, pastikan muncul `/riwayat_pemasukan` dan `/riwayat_pengeluaran`.
2. Kirim `/report`, tekan `💰 Riwayat Pemasukan`.
3. Pastikan tampil 10 riwayat terbaru maksimal per halaman.
4. Tekan `➡️ Berikutnya`, pastikan pindah halaman.
5. Tekan `🔙 Kembali ke Report`.
6. Ulangi untuk `💸 Riwayat Pengeluaran`.

---

## Suggested Commit

Setelah semua selesai:

```bash
git add src tests README.md docs/plans/2026-05-31-report-transaction-log-task-plan.md
git commit -m "feat: add income and expense transaction logs"
git push origin main
```
