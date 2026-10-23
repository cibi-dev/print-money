# PrintMoney 🖨️💰

**Profit, expense, and net income manager for a 3D printing business.**

A sleek desktop application built with Python and CustomTkinter to help small 3D printing businesses track orders, manage expenses, monitor inventory, and generate professional invoices — all from a single dashboard.

---

## Installation

### 1. Requirements
- Python 3.10 or higher
- Windows 10 / 11

### 2. Install dependencies

```bash
cd PrintMoney
pip install -r requirements.txt
```

### 3. Run the application

```bash
python main.py
```

On first launch, PrintMoney creates its data folder at `%APPDATA%\PrintMoney`
(`config.json`, `printmoney.log`, `data/printmoney.db` and `data/backups/`).
If that folder is not writable, it falls back to `%LOCALAPPDATA%\PrintMoney`
and then to `PrintMoneyData` next to the executable. If an older portable
install has `data/` and `config.json` next to `main.py` or the `.exe`, they
are copied there on first run; the originals are left untouched. Set
`PRINTMONEY_DATA_DIR` to force a specific folder.

---

## Project Structure

```
PrintMoney/
├── main.py              # Entry point – main window & sidebar
├── db_manager.py        # SQLite database (schema + CRUD)
├── requirements.txt     # Python dependencies
├── requirements-build.txt # PyInstaller
├── build.ps1            # Windows executable build
├── assets/
│   └── icons/           # UI icons
├── ui/
│   ├── dashboard.py     # Dashboard with KPIs and charts
│   ├── orders.py        # Order management
│   ├── quotes.py        # Quote history & conversion
│   ├── expenses.py      # Expense tracking
│   ├── inventory.py     # Filament inventory
│   ├── clients.py       # Client management & CRM
│   ├── catalog.py       # Product catalog for quick orders
│   ├── reports.py       # Reports and analytics
│   ├── calendar.py      # Delivery calendar
│   ├── calculator.py    # Floating cost calculator
│   └── settings.py      # General settings
└── utils/
    ├── paths.py         # %APPDATA% paths & legacy migration
    ├── quotes.py        # Quote contract, text and PDF
    ├── i18n.py          # Internationalization (EN/ES)
    ├── pdf_invoice.py   # PDF invoice generator
    ├── export.py        # Export to Excel/PDF
    └── notifications.py # Windows notifications
```

---

## Features

| Module | Description |
|--------|-------------|
| 📊 **Dashboard** | Monthly KPIs, profit chart, recent orders at a glance |
| 📦 **Orders** | Full CRUD, automatic inventory deduction, PDF invoices |
| 🧾 **Quotes** | Quote history, statuses, PDF/text and convert-to-order |
| 💸 **Expenses** | Editable categories, recurring expenses |
| 🧵 **Inventory** | Filament stock tracking with low-level alerts |
| 📋 **Catalog** | Saved product designs for quick order entry |
| 👥 **Clients** | Order history, per-client stats, and basic CRM |
| 📈 **Reports** | Bar, line, and pie charts + Excel/PDF export |
| 📅 **Calendar** | Monthly view with delivery dates highlighted |
| ⚡ **Calculator** | Floating quick-cost calculator |
| ⚙️ **Settings** | Business info, language (EN/ES), backup, notifications |

---

## Getting Started

1. Open **Settings** from the sidebar.
2. Fill in your business details (name, address, logo).
3. Set your **hourly rate** based on your costs.
4. Configure the **target margin** to get alerts when a sale falls below it.
5. Upload your logo as a `.png` file so it appears on invoices.

## Tests

The project ships with a regression suite that runs without a display and
without touching your real database (it uses a temporary copy):

```bash
python tests_regression.py   # 63 tests – data, PDF, i18n, migrations, paths, pagination
python tests_ui_smoke.py     # 19 tests – real Tkinter views and flows
python tests_atomic_io.py    # 5 tests – atomic config writes
```

## Repairing the filament inventory

Older versions did not return filament stock when an order was edited or
deleted, which left the inventory short and orphan rows in
`historial_filamento`. Run this once to fix it:

```bash
python reparar_inventario.py --dry-run   # show what would change
python reparar_inventario.py             # apply (asks for confirmation)
```

---

## Build a Windows executable

```powershell
pip install -r requirements.txt -r requirements-build.txt
.\build.ps1
# If PowerShell blocks unsigned scripts:
.\build.bat
```

The result is `dist\PrintMoney\PrintMoney.exe` (onedir). Distribute the whole
`dist\PrintMoney` folder, not only the `.exe`. Windows may show a SmartScreen
warning because the exe is not signed; choose **Run**. The app reads and
writes user data under `%APPDATA%\PrintMoney`; `pandas` is not bundled.

## Technical Notes

- **Data folder**: `%APPDATA%\PrintMoney`, with fallback to `%LOCALAPPDATA%\PrintMoney` and `PrintMoneyData` next to the exe (override with `PRINTMONEY_DATA_DIR`)
- **Database**: SQLite at `%APPDATA%\PrintMoney\data\printmoney.db` (or the active fallback folder)
- **Backups**: daily in `data\backups\backup_YYYY-MM-DD.db`; manual backups include a timestamp
- **Transactions**: every operation commits immediately; there is no simulated autosave
- **Notifications**: Uses `win10toast` with `plyer` fallback
- **Language**: Bilingual support — switch between English and Spanish instantly
- **Packaging**: PyInstaller onedir; user data and assets stay separate

---

## Troubleshooting

**`No module named 'win10toast'`:**
```bash
pip install win10toast
```

**Calendar not showing:**
```bash
pip install tkcalendar
```

**Icon issues:**  
Placeholder icons are auto-generated on first launch. To use real Feather icons, download the PNGs from [feathericons.com](https://feathericons.com) and place them in `assets/icons/` with these names: `home.png`, `orders.png`, `expenses.png`, `inventory.png`, `clients.png`, `reports.png`, `calendar.png`, `calculator.png`, `settings.png`.

---

## License

This project is open source. Feel free to use, modify, and distribute.
