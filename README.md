# MoneyManager (for Home Assistant)

[![GitHub Release](https://img.shields.io/github/release/FaserF/ha-moneymanager.svg?style=flat-square)](https://github.com/FaserF/ha-moneymanager/releases)
[![Downloads (Current release)](https://img.shields.io/github/downloads/FaserF/ha-moneymanager/latest/moneymanager.zip?label=Downloads%20(Current%20release)&style=flat-square)](https://github.com/FaserF/ha-moneymanager/releases)
[![License](https://img.shields.io/github/license/FaserF/ha-moneymanager.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-custom-orange.svg?style=flat-square)](https://hacs.xyz)
[![Add to Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=moneymanager)
[![CI Orchestrator](https://github.com/FaserF/ha-moneymanager/actions/workflows/ci-orchestrator.yml/badge.svg)](https://github.com/FaserF/ha-moneymanager/actions/workflows/ci-orchestrator.yml)

A secure and reliable Home Assistant integration for **MoneyManager (Android App - PC Manager feature by Realbyte)**. It communicates locally via direct API requests (no web scraping), provides robust offline caching when the phone app is closed, server connectivity tracking, and on-demand synchronization.

---

## 🧭 Quick Links

| | | | |
| :--- | :--- | :--- | :--- |
| [✨ Features](#-features) | [📦 Installation](#-installation) | [⚙️ Configuration](#️-configuration) | [🛡️ Security](SECURITY.md) |
| [🧱 Entities & Services](#-entities--services) | [🧑‍💻 Development](#-development) | [💖 Support](#️-support-this-project) | [📄 License](#-license) |

---

## ✨ Features

- **Direct Local API Integration (No Web Scraping)**:
  - Communicates directly with the internal REST/JSON & XML endpoints of the smartphone's PC Manager (`getInitData`, `getDashBoardData`, `getSummaryDataByPeriod`, `getDataByPeriod`, `getEachAssetChartData`).
- **Strictly Manual / On-Demand Sync (No Automatic Polling)**:
  - **Zero Background Polling**: The integration never automatically polls or checks the connection in the background. Because the PC Manager server only runs while you actively have the screen open on your phone, automatic polling is completely disabled (`update_interval = None`).
  - **Persistent Local Caching**: Financial data is securely cached to persistent Home Assistant storage (`Store`). Home Assistant always displays the last known state without error popups, connection warnings, or state resets.
- **Passcode & Unauthenticated Support**:
  - Full support for servers with or without a configured passcode/PIN (using automated HTTP POST login handshake & dynamic session tokens).
- **Comprehensive Financial Metrics & Period Comparisons (1:1 PC Manager)**:
  - **Assets & Debts**: Total Gross Assets, Net Assets, Total Liabilities/Debt, plus 12-month asset line history attributes.
  - **Current Month**: Income, Expenses, Net Balance, and **Savings Rate (%)**, plus category breakdowns.
  - **Previous Month**: Previous Month Income, Expenses, Balance, and **Previous Month Savings Rate (%)**.
  - **Current Year**: Full Current Year Income, Expenses, Balance, and **Yearly Savings Rate (%)**.
  - **Previous Year**: Full Previous Year Income, Expenses, Balance, and **Yearly Savings Rate (%)**.
  - **Account & Wallet Breakdowns**: Automatically creates sensors for each configured account/wallet/credit card (e.g. *Giro*, *Barzahlung*, *PayPal*, *Kreditkarte*, *GPay*).
  - **Transactions & Book Info**: Sensor with count and detailed list of the latest transactions (date, category, payment method, note, amount) and account book metadata.
- **Device Management & Quick Access**:
  - **"Visit Device" Link**: Direct button on the Home Assistant device card opening your PC Manager web interface.
  - **Diagnostics Support**: Native Home Assistant diagnostics download with automatic redaction of sensitive credentials.
  - **Manual Sync Button & Service**: Native button entity and `moneymanager.update_data` service.
- **Multilingual Support**:
  - Full English and German translations (informal "Du" form).

---

## 📦 Installation

### HACS (Recommended)

1. Open **HACS** in Home Assistant.
2. Click on the three dots in the top right corner and select **Custom repositories**.
3. Add `https://github.com/FaserF/ha-moneymanager` with category **Integration**.
4. Search for **MoneyManager** and click **Download**.
5. Restart Home Assistant.

### Manual Installation

1. Download the latest release `moneymanager.zip` from [Releases](https://github.com/FaserF/ha-moneymanager/releases).
2. Extract the folder into your Home Assistant directory under `custom_components/moneymanager`.
3. Restart Home Assistant.

---

## ⚙️ Requirements & Configuration

> [!IMPORTANT]
> **MoneyManager Pro / Paid Version Required**: The "PC Manager" local web server is a premium feature included with the Pro / paid version of MoneyManager:
> - 📱 **Android (Google Play Store)**: [MoneyManager (Remove Ads)](https://play.google.com/store/apps/details?id=com.realbyteapps.moneya)
> - 🍏 **iOS (Apple App Store)**: [Money Manager Expense & Budget](https://apps.apple.com/app/money-manager-expense-budget/id560481810) (In-App Pro / Premium Purchase)
>
> **Active Screen Required**: The mobile app only runs the local PC Manager server while the screen is open in the app. You must press **Start** on the PC Manager screen to allow Home Assistant to connect and sync data.

### Step-by-Step Setup:

1. In the **MoneyManager** mobile app:
   - Navigate to **More** (`...`) > **PC Manager**.
   - Tap **Start** to launch the local web server.
   - The app will display your local IP address and port (e.g. `http://192.168.1.50:8888`).
2. In Home Assistant:
   - Go to **Settings > Devices & Services > Add Integration**.
   - Search for **MoneyManager**.
   - Enter the **IP Address / Hostname** and **Port** exactly as shown in your app screen.
   - If you set a passcode in the app, enter it in the **Passcode** field.
3. Click **Submit** while the PC Manager server is actively running on your phone.

---

## 🔄 Synchronization Strategy & Offline Behavior

- **Never Automatic Polling**: The integration does **not** poll your network automatically. It only attempts communication:
  1. During the initial integration setup or options flow modification.
  2. When pressing the **Update Data Now** button (`button.moneymanager_update_data_now`).
  3. When invoking the service `moneymanager.update_data` (e.g. in automations or dashboard buttons).
- **Persistent Local Cache**: All metrics, accounts, and category tables are persisted to Home Assistant's local storage. You can freely restart Home Assistant or leave your home network without losing historical values.
- **Sync Status**: The `sensor.moneymanager_last_sync` entity records the exact date and time of the last sync and provides `server_connected` in its attributes, which shows whether the PC Manager server is currently reachable.

### Sensors
- `sensor.moneymanager_last_sync`: Timestamp of the last successful synchronization (includes `server_connected` attribute).
- **Assets & Balances**:
  - `sensor.moneymanager_total_gross_assets` (Gesamtvermögen)
  - `sensor.moneymanager_net_assets` (Nettovermögen)
  - `sensor.moneymanager_total_debt` (Gesamtschulden)
- **Current Month (Aktueller Monat)**:
  - `sensor.moneymanager_monthly_income` (Monatliche Einnahmen)
  - `sensor.moneymanager_monthly_expense` (Monatliche Ausgaben)
  - `sensor.moneymanager_monthly_balance` (Monatlicher Saldo)
  - `sensor.moneymanager_monthly_savings_rate` (Monatliche Sparquote in %)
- **Previous Month (Vormonat)**:
  - `sensor.moneymanager_prev_month_income` (Einnahmen Vormonat)
  - `sensor.moneymanager_prev_month_expense` (Ausgaben Vormonat)
  - `sensor.moneymanager_prev_month_balance` (Saldo Vormonat)
  - `sensor.moneymanager_prev_month_savings_rate` (Sparquote Vormonat in %)
- **Current Year (Aktuelles Jahr)**:
  - `sensor.moneymanager_yearly_income` (Jährliche Einnahmen)
  - `sensor.moneymanager_yearly_expense` (Jährliche Ausgaben)
  - `sensor.moneymanager_yearly_balance` (Jährlicher Saldo)
  - `sensor.moneymanager_yearly_savings_rate` (Jährliche Sparquote in %)
- **Previous Year (Vorjahr)**:
  - `sensor.moneymanager_prev_year_income` (Einnahmen Vorjahr)
  - `sensor.moneymanager_prev_year_expense` (Ausgaben Vorjahr)
  - `sensor.moneymanager_prev_year_balance` (Saldo Vorjahr)
  - `sensor.moneymanager_prev_year_savings_rate` (Sparquote Vorjahr in %)
- **Payment & Account Breakdowns**:
  - `sensor.moneymanager_cash_expense` (Monatliche Barausgaben)
  - `sensor.moneymanager_card_expense` (Monatliche Kartenausgaben)
  - Dynamic account & card sensors (`sensor.moneymanager_giro`, `sensor.moneymanager_barzahlung`, `sensor.moneymanager_paypal`, `sensor.moneymanager_kreditkarte`, etc.)
- **Book & Transactions**:
  - `sensor.moneymanager_recent_transactions` (Letzte Buchungen mit Kategorie, Betrag, Konto, Notiz)
  - `sensor.moneymanager_account_book` (Haushaltsbuch-Info)

### Button
- `button.moneymanager_update_data_now`: Manually triggers synchronization with the smartphone.

### Services
- `moneymanager.update_data`: Service call to trigger immediate data refresh from the smartphone.
- `moneymanager.create_entry`: Create a new transaction in MoneyManager (*Ausgabe, Einnahme oder Umbuchung*). Parameters:
  - `amount`: Number (e.g. `12.50`)
  - `entry_type`: `Expense`, `Income`, or `Transfer`
  - `category`: Category name (e.g. `Lebensmittel`, `Gehalt`, `Freizeit`)
  - `account`: Account/card name (e.g. `Giro`, `Barzahlung`, `PayPal`, `Kreditkarte`)
  - `date`: Optional date in `YYYY-MM-DD` format (defaults to current date)
  - `note`: Optional payee or short summary
  - `detail`: Optional memo / description
  - `to_account`: Target account for transfers
- `moneymanager.delete_entry`: Delete an existing transaction by ID (`entry_id`).

---

## ❤️ Support This Project

> I maintain this integration in my free time. If you find it useful, consider supporting the development!

<div align="center">

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor%20on-GitHub-%23EA4AAA?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/FaserF)&nbsp;&nbsp;
[![PayPal](https://img.shields.io/badge/Donate%20via-PayPal-%2300457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/FaserF)

</div>

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
