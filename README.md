# SolarCloud — AI-Powered Solar Proposal Platform

> Built for **Energybae, Pune** · Automates the full journey from electricity bill to a professional solar proposal in under 10 seconds.

---

## What It Does

Upload any Indian electricity bill (PDF or image). The platform uses **Google Gemini Vision AI** to read it, extract every key field, compute the right solar system size, and generate a downloadable package — an **Excel sizing report** and a **branded PDF proposal** — without any manual data entry.

---

## Live Demo Flow

```
Upload Bill  ──►  AI Extracts Data  ──►  Review & Edit  ──►  Download ZIP
 (PDF/Image)       (Gemini Vision)       (Live ROI Chart)    (Excel + PDF)
```

---

## Screenshots

| Step 1 — Upload | Step 2 — Analysis | Step 3 — Download |
|---|---|---|
| Drag-drop bill or browse | Dark KPI card + ROI chart | Proposal ready to download |

---

## Features

- **AI Extraction** — Gemini 1.5 Flash Vision reads MSEDCL, Adani, Tata Power, BEST, and all Indian state utility bills
- **Smart Fallbacks** — If a field is missing, the extractor calculates it (e.g. `units = current_reading − previous_reading`)
- **Live ROI Chart** — Interactive Chart.js bar chart updates in real-time as you edit any field
- **KPI Dashboard** — Dark performance card shows units, rate, sanctioned load, monthly bill, and recommended solar size instantly
- **Solar System Points** — Sizing list with panel count, roof area, system cost, annual savings, and payback period
- **Excel Report** — Two-sheet workbook: Bill Data (inputs) + Solar Calculation (formula-driven, never overwritten)
- **PDF Proposal** — 3-page branded ReportLab PDF: cover page, system sizing table, and financial ROI table
- **ZIP Download** — Both files bundled together in a single download
- **Editable Review** — Every extracted field is editable before generating the report
- **JSON Repair** — Auto-fixes truncated Gemini responses so extraction never silently fails

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13 · Flask 3.1 · Flask-CORS |
| AI / Vision | Google Gemini 1.5 Flash (`gemini-flash-latest`) |
| Excel | openpyxl 3.1 |
| PDF | ReportLab (SimpleDocTemplate + Platypus) |
| Frontend | Vanilla JS · Chart.js 4.4.4 |
| Fonts | Inter (Google Fonts) |
| Environment | python-dotenv |

---

## Project Structure

```
EnergyBea_assignment/
│
├── app.py                          # Flask app — API routes & request handling
├── config.py                       # Paths, API key, solar defaults (₹55K/kW, 5h sun, etc.)
├── requirements.txt                # Python dependencies
├── start.sh                        # macOS startup script (libexpat workaround)
├── .env                            # API key (not committed)
├── .env.example                    # Template for .env
│
├── services/
│   ├── extractor.py                # Gemini Vision call · JSON repair · validation
│   ├── excel_handler.py            # Excel template creation & population
│   └── pdf_generator.py           # 3-page ReportLab PDF proposal
│
├── static/
│   ├── index.html                  # Sopanel-inspired dashboard UI (3-step wizard)
│   ├── style.css                   # Dark perf-card · yellow/green theme · sidebar layout
│   └── script.js                   # Step control · extraction · live chart · ZIP download
│
├── templates/
│   └── solar_calculator_template.xlsx   # Auto-generated Excel template
│
├── uploads/                        # Temporarily stores uploaded bills (auto-created)
└── outputs/                        # Generated Excel reports (auto-created)
```

---

## Setup

### Prerequisites

- Python 3.10+
- A Google Gemini API key — free at [aistudio.google.com](https://aistudio.google.com)

### 1. Clone & enter the project

```bash
git clone <repo-url>
cd EnergyBea_assignment
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your Gemini API key

```bash
cp .env.example .env
# Open .env and set:
# GEMINI_API_KEY=your_key_here
```

### 5. Start the server

```bash
python app.py
```

Open **http://localhost:5001** in your browser.

> **macOS 26 / macOS Sequoia note** — If you hit a `pyexpat` ImportError, use the provided startup script instead:
> ```bash
> chmod +x start.sh && ./start.sh
> ```
> This sets `DYLD_LIBRARY_PATH` to use Homebrew's libexpat (`brew install expat` required).

---

## API Reference

### `GET /api/health`
Returns server status and configuration check.

```json
{
  "status": "ok",
  "gemini_configured": true,
  "template_exists": true,
  "timestamp": "2026-05-05T10:30:00"
}
```

---

### `POST /api/extract`
Upload an electricity bill and extract data using Gemini Vision.

**Request:** `multipart/form-data` with field `file` (PDF, PNG, JPG, WEBP, BMP, TIFF — max 10 MB)

**Response:**
```json
{
  "success": true,
  "data": {
    "consumer_name": "MR. ADITYA DESHMUKH",
    "consumer_number": "610290087432",
    "billing_period": "MARCH 2026",
    "units_consumed": 560,
    "sanctioned_load": 7.5,
    "tariff_category": "LT-II Residential",
    "total_bill_amount": 7028.24,
    "electricity_rate": 12.55,
    "meter_number": "MSED778899",
    "supply_type": "Single Phase",
    "due_date": "20-APR-2026",
    "previous_reading": 15420,
    "current_reading": 15980,
    "additional_info": "MSEDCL Pune Urban Division"
  },
  "source_file": "bill.pdf"
}
```

---

### `POST /api/generate`
Generate a ZIP file containing the Excel report and PDF proposal.

**Request:** `application/json` — same fields as extraction output (user-edited)

**Response:** Binary ZIP download (`Energybae_Solar_Proposal.zip`) containing:
- `solar_report_NAME_TIMESTAMP.xlsx`
- `Energybae_Solar_Proposal.pdf`

```bash
# Example curl
curl -X POST http://localhost:5001/api/generate \
  -H "Content-Type: application/json" \
  -o proposal.zip \
  -d '{
    "consumer_name": "Rahul Sharma",
    "units_consumed": 320,
    "sanctioned_load": 5.0,
    "total_bill_amount": 2800,
    "electricity_rate": 8.75,
    "billing_period": "March 2026"
  }'
```

---

## Excel Output Structure

### Sheet 1 — Bill Data *(Input cells, yellow fill)*

| Cell | Field |
|---|---|
| B3 | Consumer Name |
| B4 | Consumer Number |
| B5 | Billing Period |
| B6 | Units Consumed (kWh) |
| B7 | Sanctioned Load (kW) |
| B8 | Tariff Category |
| B9 | Total Bill Amount (₹) |
| B10 | Electricity Rate (₹/kWh) |

### Sheet 2 — Solar Calculation *(Formula cells, green fill — never overwritten)*

| Output | Logic |
|---|---|
| Recommended System Size (kW) | `Daily kWh ÷ 5 peak sun hours` |
| Number of Panels | `System kW × 1000 ÷ 540W per panel` |
| Roof Area Required (sq ft) | `Panels × 20 sq ft` |
| Annual Generation (kWh) | `System kW × 5h × 365 days` |
| Annual Savings (₹) | `Units generated × electricity rate` |
| Govt Subsidy (₹) | `₹30K/kW ≤ 2kW · ₹18K/kW for 3rd kW` |
| Net Investment (₹) | `System cost − subsidy` |
| Payback Period (years) | `Net investment ÷ annual savings` |
| 25-Year Savings (₹) | `Compounded at 5% tariff escalation` |
| CO₂ Offset (tonnes/year) | `Generation × 0.82 kg/kWh ÷ 1000` |

---

## Sizing Formulas (JS + PDF mirror the Excel logic)

```
recommended_kw  = ⌈ units_consumed / 120 ⌉
panel_count     = ⌈ kw × 1000 / 400 ⌉       ← 400W panels
roof_area       = kw × 100  sq.ft
system_cost     = kw × ₹55,000
annual_savings  = monthly_bill × 12 × 0.90   ← 90% bill reduction
payback_years   = system_cost / annual_savings
savings_25yr    = Σ(annual_savings × 1.03^k, k=0..24) − system_cost
```

---

## Supported Utility Bills

| Utility | Region |
|---|---|
| MSEDCL | Maharashtra (Pune, Nagpur, etc.) |
| Adani Electricity | Mumbai suburbs |
| Tata Power | Mumbai, Delhi |
| BEST | Brihanmumbai |
| KSEB | Kerala |
| BESCOM | Karnataka |
| TANGEDCO | Tamil Nadu |
| Any Indian SEB | Generic fallback |

---

## Design Decisions

**Formula-safe Excel writes** — `excel_handler.py` inspects each target cell before writing. If the cell starts with `=`, it is skipped entirely. Input cells are populated; formula cells are never touched.

**AI-first, fallback-second** — Gemini Vision handles all parsing. When a field is missing (e.g. `units_consumed`), the extractor automatically computes it from `current_reading − previous_reading`. When `electricity_rate` is absent, it is derived as `total_bill_amount ÷ units_consumed`.

**Resilient JSON parsing** — Gemini occasionally returns truncated JSON. `_repair_json()` closes open braces and retries `json.loads()` before raising an error. The entire extraction is also retried once on failure.

**Live UI computation** — The ROI chart, KPI cards, and sizing list all recompute on every field edit in the browser using the same math as the backend — so what users see during review exactly matches the generated report.

**In-memory ZIP** — The ZIP is built in a `BytesIO` buffer and streamed directly — no temporary ZIP file is written to disk.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google Gemini API key from [aistudio.google.com](https://aistudio.google.com) |

---

## Solar Defaults (`config.py`)

| Parameter | Value |
|---|---|
| Peak Sun Hours | 5.0 hrs/day (India average) |
| Panel Wattage | 540W |
| Cost per kW | ₹55,000 |
| System Life | 25 years |
| Annual Tariff Increase | 5% |
| Annual Degradation | 0.5% |
| CO₂ Factor | 0.82 kg/kWh (India grid) |

---

## License

Internal project — Energybae, Pune. Not for public distribution.
