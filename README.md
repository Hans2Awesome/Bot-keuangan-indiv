# Bot04 — Telegram Personal Finance Tracker

Bot04 adalah chatbot Telegram untuk mencatat pemasukan, pengeluaran, investasi, dan menampilkan laporan keuangan personal per user Telegram.

## Fitur MVP

- Input cepat lewat teks bebas, misalnya `makan 25000`.
- Preview transaksi sebelum disimpan.
- Konfirmasi dengan tombol `✅ Simpan` / `❌ Batal`.
- Flow tombol manual untuk pemasukan, pengeluaran, dan investasi.
- Laporan harian, mingguan, bulanan, kategori, dan investasi.
- Data dipisahkan per user Telegram berdasarkan `telegram_user_id`.
- Storage lokal SQLite.

## Setup Lokal

### 1. Clone / masuk ke folder project

```bash
cd /root/projects/bot04
```

### 2. Buat virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

Jika environment sudah tersedia, cukup aktifkan environment tersebut.

### 3. Install package

```bash
python -m pip install -e .
```

Untuk kebutuhan development/test:

```bash
python -m pip install -e .[dev]
```

### 4. Buat file konfigurasi

Copy `.env.example` ke `.env`:

```bash
cp .env.example .env
```

Lalu isi `BOT_TOKEN` di `.env` dengan token bot Telegram dari BotFather.

Contoh isi `.env`:

```env
BOT_TOKEN=isi_token_bot_di_sini
DATABASE_PATH=bot04.sqlite3
TIMEZONE=Asia/Jakarta
CURRENCY=IDR
```

Jangan commit `.env` karena berisi token rahasia.

## Cara Menjalankan Bot

Cek konfigurasi tanpa menjalankan polling Telegram:

```bash
python -m bot04.main --dry-run
```

Jalankan bot:

```bash
python -m bot04.main
```

Jika `BOT_TOKEN` sudah benar, bot akan mulai polling dan siap menerima pesan Telegram.

## Cara Menjalankan Test

Jalankan seluruh test:

```bash
pytest
```

Atau:

```bash
python -m pytest -q
```

Jalankan test tertentu:

```bash
python -m pytest tests/test_help_text.py -q
```

## Cara Pakai Bot

Mulai dari Telegram:

```text
/start
```

Buka menu utama:

```text
/menu
```

Buka bantuan:

```text
/help
```

## Input Cepat

Cara tercepat mencatat transaksi adalah langsung mengetik pesan.

Contoh input cepat:

```text
makan 25000
kopi 25k kemarin
gojek 15000 kantor
gaji 5000000
invest btc 100000 dca mingguan
```

Bot akan membaca nominal, kategori, tipe transaksi, tanggal, dan catatan jika tersedia. Setelah itu bot menampilkan preview. Tekan `✅ Simpan` jika sudah benar.

## Tombol Manual

Menu utama menyediakan tombol:

- `➕ Pemasukan`
- `➖ Pengeluaran`
- `📈 Investasi`
- `📊 Laporan`
- `🗂 Kategori`
- `⚙️ Pengaturan`

Flow manual MVP:

1. Pilih tipe transaksi dari tombol.
2. Pilih kategori.
3. Masukkan nominal dan catatan opsional.
4. Cek preview.
5. Tekan `✅ Simpan` untuk menyimpan atau `❌ Batal` untuk membatalkan.

## Laporan

Command laporan:

```text
/today
/week
/month
/report
```

- `/today`: laporan hari ini.
- `/week`: laporan minggu berjalan.
- `/month`: laporan bulan berjalan.
- `/report`: menu pilihan laporan.
- `/riwayat_pemasukan`: melihat riwayat pemasukan, 10 data per halaman, terbaru dulu.
- `/riwayat_pengeluaran`: melihat riwayat pengeluaran, 10 data per halaman, terbaru dulu.

## Struktur Project

```text
bot04/
├── README.md
├── pyproject.toml
├── .env.example
├── docs/
├── src/
│   └── bot04/
│       ├── bot/
│       ├── database/
│       ├── reports/
│       └── services/
└── tests/
```

## Catatan Keamanan

- `.env` tidak boleh dipush ke GitHub.
- `BOT_TOKEN` jangan ditampilkan di log atau chat.
- Database SQLite default berada di `bot04.sqlite3`.
