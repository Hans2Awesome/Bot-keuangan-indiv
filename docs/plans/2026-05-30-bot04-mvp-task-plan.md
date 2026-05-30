# Bot04 MVP Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Membangun chatbot Telegram pencatat pemasukan, pengeluaran, dan investasi per user Telegram, dengan prioritas utama input cepat lewat teks.

**Architecture:** Bot04 memakai arsitektur modular: handler Telegram hanya mengurus command/callback/message routing, service layer mengurus business logic, database layer mengurus SQLite, dan report layer mengurus agregasi laporan. Input cepat teks dipisahkan ke parser khusus agar bisa dites mandiri dan mudah dikembangkan.

**Tech Stack:** Python 3.11+, python-telegram-bot, SQLite, pytest, python-dotenv.

---

## Prinsip Implementasi

- Data wajib dipisahkan per `telegram_user_id`.
- Input cepat teks adalah fitur utama, bukan tambahan.
- Semua transaksi dari input cepat tetap harus preview + konfirmasi sebelum disimpan.
- Gunakan SQLite untuk storage lokal.
- Gunakan TDD untuk logic utama: parser, repository, service, report.
- Handler Telegram boleh dites dengan unit test ringan tanpa koneksi Telegram asli.
- MVP tidak menghitung profit/loss investasi real-time; hanya total uang yang dialokasikan ke investasi.

---

## Phase 1 — Project Foundation

### Task 1: Buat Struktur Project Python

**Objective:** Membuat struktur file awal agar project siap diisi kode.

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `src/bot04/__init__.py`
- Create: `src/bot04/main.py`
- Create: `src/bot04/config.py`
- Create: `tests/__init__.py`

**Steps:**
1. Buat package `bot04` di `src/bot04`.
2. Tambahkan dependency minimum:
   - `python-telegram-bot`
   - `python-dotenv`
   - `pytest`
3. Buat `.env.example` berisi `BOT_TOKEN=` dan `DATABASE_PATH=bot04.sqlite3`.
4. Buat `config.py` untuk baca environment.
5. Verifikasi import package.

**Verification:**

```bash
cd projects/bot04
python -m pytest -q
python -c "import bot04; print('ok')"
```

Expected: pytest berjalan tanpa error, import `bot04` berhasil.

---

### Task 2: Buat Config Loader

**Objective:** Membaca token bot, database path, timezone, dan currency dari environment.

**Files:**
- Create/Modify: `src/bot04/config.py`
- Test: `tests/test_config.py`

**Behavior:**
- Default timezone: `Asia/Jakarta`.
- Default currency: `IDR`.
- Default database path: `bot04.sqlite3`.
- `BOT_TOKEN` boleh kosong saat test.

**TDD Steps:**
1. Tulis test bahwa config memakai default jika env tidak diisi.
2. Run test dan pastikan fail karena loader belum ada.
3. Implement `load_config()`.
4. Run test sampai pass.

**Verification:**

```bash
pytest tests/test_config.py -q
```

---

## Phase 2 — Domain Model dan Database

### Task 3: Definisikan Domain Type Transaksi

**Objective:** Membuat enum/constant untuk tipe transaksi.

**Files:**
- Create: `src/bot04/domain.py`
- Test: `tests/test_domain.py`

**Types:**
- `income`
- `expense`
- `investment`

**TDD Steps:**
1. Test bahwa tipe transaksi valid hanya 3 nilai tersebut.
2. Implement constant/enum.
3. Test helper label Indonesia: income → Pemasukan, expense → Pengeluaran, investment → Investasi.

**Verification:**

```bash
pytest tests/test_domain.py -q
```

---

### Task 4: Buat SQLite Schema

**Objective:** Membuat tabel inti untuk user, category, transaction, dan wallet opsional.

**Files:**
- Create: `src/bot04/database/connection.py`
- Create: `src/bot04/database/schema.py`
- Test: `tests/test_schema.py`

**Tables:**

`users`:
- `id`
- `telegram_user_id` unique
- `first_name`
- `username`
- `timezone`
- `currency`
- `created_at`

`categories`:
- `id`
- `user_id`
- `type`
- `name`
- `aliases`
- `is_default`
- unique per `user_id,type,name`

`transactions`:
- `id`
- `user_id`
- `type`
- `category_id`
- `amount`
- `note`
- `asset_name`
- `transaction_date`
- `created_at`
- `updated_at`

`wallets` untuk fase lanjut boleh dibuat sekarang tapi tidak wajib dipakai.

**TDD Steps:**
1. Test `init_db()` membuat semua tabel.
2. Test constraint unique user Telegram ID.
3. Implement schema.
4. Run test.

**Verification:**

```bash
pytest tests/test_schema.py -q
```

---

### Task 5: Buat User Repository

**Objective:** Membuat fungsi get-or-create user berdasarkan Telegram user ID.

**Files:**
- Create: `src/bot04/database/users.py`
- Test: `tests/test_users_repository.py`

**Behavior:**
- Jika user belum ada, insert user baru.
- Jika user sudah ada, return user yang sama.
- Tidak boleh membuat duplikat untuk Telegram user ID yang sama.

**Verification:**

```bash
pytest tests/test_users_repository.py -q
```

---

### Task 6: Buat Default Category Seeder

**Objective:** Membuat kategori default otomatis per user.

**Files:**
- Create: `src/bot04/database/categories.py`
- Test: `tests/test_categories_repository.py`

**Default Income:**
- Gaji: aliases `gaji,salary`
- Bonus: aliases `bonus`
- Freelance: aliases `freelance,project`
- Bisnis: aliases `bisnis,jualan,usaha`
- Hadiah: aliases `hadiah,gift`
- Lainnya: aliases `lainnya,lain`

**Default Expense:**
- Makan & Minum: aliases `makan,minum,kopi,sarapan,makan siang,makan malam`
- Transportasi: aliases `transport,transportasi,gojek,grab,bensin,parkir`
- Belanja: aliases `belanja,shopping,beli`
- Tagihan: aliases `tagihan,listrik,air,internet,pulsa`
- Hiburan: aliases `hiburan,nonton,game`
- Kesehatan: aliases `kesehatan,dokter,obat`
- Pendidikan: aliases `pendidikan,sekolah,kursus,buku`
- Lainnya: aliases `lainnya,lain`

**Default Investment:**
- Saham: aliases `saham,stock,bbca,bmri`
- Crypto: aliases `crypto,kripto,btc,eth,bitcoin,ethereum`
- Reksadana: aliases `reksadana,rd`
- Emas: aliases `emas,gold,antam`
- Deposito: aliases `deposito`
- Lainnya: aliases `investasi,lainnya,lain`

**Behavior:**
- Seeder idempotent; dipanggil berkali-kali tidak membuat duplikat.
- Alias dipakai oleh parser input cepat.

**Verification:**

```bash
pytest tests/test_categories_repository.py -q
```

---

### Task 7: Buat Transaction Repository

**Objective:** Menyimpan, mengambil, mengedit, dan menghapus transaksi per user.

**Files:**
- Create: `src/bot04/database/transactions.py`
- Test: `tests/test_transactions_repository.py`

**Behavior:**
- Create transaction.
- List transaksi berdasarkan user dan range tanggal.
- Update nominal/kategori/tanggal/catatan.
- Delete transaction.
- Query tidak boleh bocor antar user.

**Verification:**

```bash
pytest tests/test_transactions_repository.py -q
```

---

## Phase 3 — Fast Text Input Parser, Prioritas Utama

### Task 8: Buat Money Parser

**Objective:** Membaca nominal dari teks Indonesia secara fleksibel.

**Files:**
- Create: `src/bot04/services/money_parser.py`
- Test: `tests/test_money_parser.py`

**Input yang harus didukung:**
- `25000` → 25000
- `25.000` → 25000
- `25,000` → 25000
- `Rp25.000` → 25000
- `rp 25.000` → 25000
- `25k` → 25000
- `1.5jt` → 1500000
- `1,5 juta` → 1500000

**TDD Steps:**
1. Test tiap format nominal.
2. Test input tanpa nominal mengembalikan error yang jelas.
3. Implement parser minimal.
4. Run test.

**Verification:**

```bash
pytest tests/test_money_parser.py -q
```

---

### Task 9: Buat Date Parser Ringan

**Objective:** Membaca tanggal dari input cepat jika user menyebut hari ini/kemarin/tanggal manual.

**Files:**
- Create: `src/bot04/services/date_parser.py`
- Test: `tests/test_date_parser.py`

**Input yang didukung MVP:**
- tidak ada tanggal → hari ini WIB
- `hari ini` → hari ini
- `kemarin` → H-1
- `30/05/2026`
- `2026-05-30`

**Behavior:**
- Parser mengembalikan tanggal transaksi dan teks yang sudah dibersihkan dari token tanggal.

**Verification:**

```bash
pytest tests/test_date_parser.py -q
```

---

### Task 10: Buat Category Matcher Berbasis Alias

**Objective:** Menebak kategori dan tipe transaksi dari kata-kata input cepat.

**Files:**
- Create: `src/bot04/services/category_matcher.py`
- Test: `tests/test_category_matcher.py`

**Behavior:**
- `gaji 5000000` → income, Gaji
- `bonus 100000` → income, Bonus
- `makan 25000` → expense, Makan & Minum
- `gojek 15000` → expense, Transportasi
- `invest btc 100000` → investment, Crypto, asset `BTC`
- `emas 500000` → investment, Emas, asset `Emas` atau kosong sesuai desain final
- Jika tidak yakin, fallback ke `expense/Lainnya` tapi preview harus memberi status `needs_review=True`.

**Important:** Jangan langsung simpan hasil parser tanpa konfirmasi user.

**Verification:**

```bash
pytest tests/test_category_matcher.py -q
```

---

### Task 11: Buat Quick Input Parser Utama

**Objective:** Menggabungkan money parser, date parser, dan category matcher menjadi satu hasil preview transaksi.

**Files:**
- Create: `src/bot04/services/quick_input_parser.py`
- Test: `tests/test_quick_input_parser.py`

**Output object fields:**
- `type`
- `category_name`
- `amount`
- `note`
- `asset_name`
- `transaction_date`
- `confidence`
- `needs_review`
- `original_text`

**Contoh wajib:**
- `makan 25000` → expense, Makan & Minum, 25000, note kosong
- `transport 15000 gojek` → expense, Transportasi, 15000, note `gojek`
- `gaji 5000000` → income, Gaji, 5000000
- `invest btc 100000` → investment, Crypto, 100000, asset `BTC`
- `btc 100000 dca mingguan` → investment, Crypto, 100000, asset `BTC`, note `dca mingguan`
- `kopi 25k kemarin` → expense, Makan & Minum, 25000, tanggal kemarin

**Error Handling:**
- Tidak ada nominal → return error `Nominal belum ditemukan`.
- Nominal 0 atau negatif → return error `Nominal harus lebih dari 0`.
- Teks kosong → return error `Tulis transaksi dulu`.

**Verification:**

```bash
pytest tests/test_quick_input_parser.py -q
```

---

### Task 12: Format Preview Transaksi dari Input Cepat

**Objective:** Membuat teks preview yang mudah dibaca user sebelum transaksi disimpan.

**Files:**
- Create: `src/bot04/services/transaction_preview.py`
- Test: `tests/test_transaction_preview.py`

**Example:**

```text
Saya mendeteksi transaksi:
Tipe: Pengeluaran
Kategori: Makan & Minum
Nominal: Rp25.000
Catatan: -
Tanggal: 30 Mei 2026

Benar?
```

**Behavior:**
- Format Rupiah dengan titik ribuan.
- Label tipe dalam bahasa Indonesia.
- Jika `needs_review=True`, tambahkan peringatan:
  `Saya belum terlalu yakin dengan kategorinya. Silakan cek sebelum simpan.`

**Verification:**

```bash
pytest tests/test_transaction_preview.py -q
```

---

## Phase 4 — Service Layer

### Task 13: Buat Transaction Service untuk Simpan dari Preview

**Objective:** Menyimpan transaksi yang sudah dikonfirmasi user.

**Files:**
- Create: `src/bot04/services/transaction_service.py`
- Test: `tests/test_transaction_service.py`

**Behavior:**
- Terima parsed preview.
- Cari category milik user berdasarkan type + name.
- Simpan transaction.
- Return summary transaksi tersimpan.
- Tidak simpan jika kategori tidak valid.

**Verification:**

```bash
pytest tests/test_transaction_service.py -q
```

---

### Task 14: Buat Pending Confirmation Store

**Objective:** Menyimpan sementara hasil parsing input cepat sampai user tekan `✅ Simpan` atau `❌ Batal`.

**Files:**
- Create: `src/bot04/services/pending_store.py`
- Test: `tests/test_pending_store.py`

**MVP Option:**
- In-memory dict dengan key `telegram_user_id`.
- Simpan parsed transaction + timestamp.
- Expire setelah 10 menit.

**Behavior:**
- Set pending preview.
- Get pending preview.
- Clear pending setelah simpan/batal.
- User A tidak bisa melihat pending User B.

**Verification:**

```bash
pytest tests/test_pending_store.py -q
```

---

## Phase 5 — Reports

### Task 15: Buat Date Range Helper untuk Laporan

**Objective:** Menghasilkan range tanggal harian, mingguan, bulanan berdasarkan timezone Asia/Jakarta.

**Files:**
- Create: `src/bot04/reports/date_ranges.py`
- Test: `tests/test_date_ranges.py`

**Behavior:**
- `today_range()`
- `week_range()` mulai Senin.
- `month_range()` mulai tanggal 1 sampai akhir bulan.

**Verification:**

```bash
pytest tests/test_date_ranges.py -q
```

---

### Task 16: Buat Report Aggregator

**Objective:** Menghitung total pemasukan, pengeluaran, investasi, sisa bersih, dan rata-rata pengeluaran.

**Files:**
- Create: `src/bot04/reports/aggregator.py`
- Test: `tests/test_report_aggregator.py`

**Behavior:**
- Total per tipe transaksi.
- Net = income - expense - investment.
- Top expense categories.
- Investment percentage = investment / income * 100 jika income > 0.

**Verification:**

```bash
pytest tests/test_report_aggregator.py -q
```

---

### Task 17: Buat Report Formatter

**Objective:** Membuat teks laporan harian, mingguan, bulanan, kategori, dan investasi.

**Files:**
- Create: `src/bot04/reports/formatter.py`
- Test: `tests/test_report_formatter.py`

**Reports:**
- Harian
- Mingguan
- Bulanan
- Kategori pemasukan
- Kategori pengeluaran
- Investasi

**Verification:**

```bash
pytest tests/test_report_formatter.py -q
```

---

## Phase 6 — Telegram Bot Handlers

### Task 18: Buat Main Menu Keyboard

**Objective:** Membuat inline keyboard menu utama.

**Files:**
- Create: `src/bot04/bot/keyboards.py`
- Test: `tests/test_keyboards.py`

**Buttons:**
- `➕ Pemasukan`
- `➖ Pengeluaran`
- `📈 Investasi`
- `📊 Laporan`
- `🗂 Kategori`
- `⚙️ Pengaturan`

**Verification:**

```bash
pytest tests/test_keyboards.py -q
```

---

### Task 19: Buat `/start` dan `/menu` Handler

**Objective:** Mendaftarkan user, seed kategori, lalu menampilkan menu utama.

**Files:**
- Create: `src/bot04/bot/handlers_start.py`
- Test: `tests/test_handlers_start.py`

**Behavior:**
- `/start` get-or-create user.
- Seed kategori default.
- Kirim pesan sambutan + keyboard.

**Verification:**

```bash
pytest tests/test_handlers_start.py -q
```

---

### Task 20: Buat Message Handler untuk Input Cepat

**Objective:** Saat user mengetik transaksi bebas, bot parse dan tampilkan preview + tombol konfirmasi.

**Files:**
- Create: `src/bot04/bot/handlers_quick_input.py`
- Test: `tests/test_handlers_quick_input.py`

**Behavior:**
- Abaikan command yang diawali `/`.
- Parse teks dengan `quick_input_parser`.
- Jika error, kirim pesan bantuan singkat.
- Jika sukses, simpan ke pending store.
- Kirim preview dengan tombol:
  - `✅ Simpan`
  - `✏️ Edit`
  - `❌ Batal`

**Examples:**
- User: `makan 25000`
- Bot: preview pengeluaran Makan & Minum Rp25.000.

**Verification:**

```bash
pytest tests/test_handlers_quick_input.py -q
```

---

### Task 21: Buat Callback Handler untuk Simpan/Batal Input Cepat

**Objective:** Menangani tombol konfirmasi input cepat.

**Files:**
- Create: `src/bot04/bot/handlers_confirm.py`
- Test: `tests/test_handlers_confirm.py`

**Behavior:**
- `quick_save`: ambil pending user, simpan transaksi, clear pending, edit pesan jadi sukses.
- `quick_cancel`: clear pending, edit pesan jadi batal.
- Jika pending tidak ada/expired, tampilkan pesan expired.

**Verification:**

```bash
pytest tests/test_handlers_confirm.py -q
```

---

### Task 22: Buat Report Command Handlers

**Objective:** Menyediakan `/today`, `/week`, `/month`, `/report`.

**Files:**
- Create: `src/bot04/bot/handlers_reports.py`
- Test: `tests/test_handlers_reports.py`

**Behavior:**
- `/today` tampilkan laporan hari ini.
- `/week` tampilkan laporan minggu ini.
- `/month` tampilkan laporan bulan ini.
- `/report` tampilkan menu pilihan laporan.

**Verification:**

```bash
pytest tests/test_handlers_reports.py -q
```

---

### Task 23: Buat Bot Application Wiring

**Objective:** Menghubungkan semua handler ke aplikasi Telegram.

**Files:**
- Modify: `src/bot04/main.py`
- Create: `src/bot04/bot/app.py`
- Test: `tests/test_bot_app.py`

**Behavior:**
- Register command handlers.
- Register callback query handlers.
- Register message handler untuk input cepat.
- `main.py` menjalankan polling jika token tersedia.

**Verification:**

```bash
pytest tests/test_bot_app.py -q
python -m bot04.main --dry-run
```

---

## Phase 7 — Manual Flows dan Polish

### Task 24: Buat Manual Flow Pemasukan

**Objective:** Menyediakan flow tombol bertahap untuk user yang tidak ingin input cepat.

**Files:**
- Create: `src/bot04/bot/handlers_manual_income.py`
- Test: `tests/test_handlers_manual_income.py`

**Scope MVP:**
- Pilih kategori.
- Input nominal.
- Preview.
- Simpan/batal.

---

### Task 25: Buat Manual Flow Pengeluaran

**Objective:** Menyediakan flow tombol bertahap untuk pengeluaran.

**Files:**
- Create: `src/bot04/bot/handlers_manual_expense.py`
- Test: `tests/test_handlers_manual_expense.py`

---

### Task 26: Buat Manual Flow Investasi

**Objective:** Menyediakan flow tombol bertahap untuk investasi.

**Files:**
- Create: `src/bot04/bot/handlers_manual_investment.py`
- Test: `tests/test_handlers_manual_investment.py`

---

### Task 27: Buat Edit/Hapus Transaksi Dasar

**Objective:** User bisa menghapus atau mengedit transaksi dari daftar detail.

**Files:**
- Create: `src/bot04/bot/handlers_transactions.py`
- Test: `tests/test_handlers_transactions.py`

**MVP Scope:**
- List transaksi terakhir.
- Hapus transaksi dengan konfirmasi.
- Edit nominal/catatan sederhana.

---

### Task 28: Buat Help Text yang Mengutamakan Input Cepat

**Objective:** Membantu user memahami cara input cepat.

**Files:**
- Create: `src/bot04/bot/help_text.py`
- Test: `tests/test_help_text.py`

**Isi Help:**

```text
Contoh input cepat:
- makan 25000
- kopi 25k kemarin
- gojek 15000 kantor
- gaji 5000000
- invest btc 100000 dca mingguan
```

---

### Task 29: Tambahkan README Setup dan Cara Run

**Objective:** Dokumentasi cara install, konfigurasi token, run bot, dan menjalankan test.

**Files:**
- Modify: `README.md`

**Must Include:**
- Copy `.env.example` ke `.env`.
- Isi `BOT_TOKEN`.
- Jalankan `python -m bot04.main`.
- Jalankan `pytest`.

---

### Task 30: Full Test dan Smoke Test

**Objective:** Memastikan MVP siap dicoba manual di Telegram.

**Files:**
- No new files.

**Commands:**

```bash
pytest -q
python -m bot04.main --dry-run
```

**Manual Telegram Smoke Test:**
1. `/start`
2. `makan 25000`
3. Tekan `✅ Simpan`
4. `/today`
5. `gaji 5000000`
6. Tekan `✅ Simpan`
7. `invest btc 100000 dca`
8. Tekan `✅ Simpan`
9. `/month`

Expected:
- Semua transaksi tersimpan ke user yang sama.
- Laporan menampilkan pemasukan, pengeluaran, dan investasi dengan benar.

---

## Suggested Implementation Order

Prioritas tertinggi:

1. Task 1–7: fondasi + database.
2. Task 8–12: input cepat teks sampai preview.
3. Task 13–14: simpan setelah konfirmasi.
4. Task 20–21: integrasi Telegram untuk input cepat.
5. Task 15–17 + 22: laporan.
6. Task 18–19 + 23: wiring menu/start/app.
7. Task 24–30: manual flows, polish, docs, smoke test.

Kalau ingin MVP tercepat, kerjakan sampai Task 23 dulu. Manual flow tombol bisa menyusul karena input cepat teks adalah prioritas utama.
