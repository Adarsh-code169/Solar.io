# ⚡ Solar Load Calculator — Electricity Bill to Excel Automation

> **Energybae, Pune** — Automate the entire workflow from electricity bill upload to solar system recommendation in seconds.

---

## 🚀 What It Does

1. **Upload** — Drag-and-drop an electricity bill (PDF or image)
2. **AI Extract** — Google Gemini Vision reads the bill and extracts key fields
3. **Review** — Edit any field before generating the report
4. **Download** — Get a filled Excel file with solar recommendations, savings, and ROI

---

## 📁 Folder Structure

```
EnergyBea_assignment/
├── app.py                    # Flask web application (main entry point)
├── config.py                 # Configuration & environment variables
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── README.md                 # This file
│
├── services/
│   ├── extractor.py          # Gemini AI bill data extraction
│   └── excel_handler.py      # Excel template creation & population
│
├── templates/
│   └── solar_calculator_template.xlsx  # Auto-generated Excel template
│
├── static/
│   ├── index.html            # Web UI
│   ├── style.css             # Premium dark-themed styles
│   └── script.js             # Frontend logic
│
├── uploads/                  # Temporary uploaded bills (auto-created)
└── outputs/                  # Generated Excel reports (auto-created)
```

---

## ⚙️ Setup Instructions

### 1. Prerequisites
- Python 3.9+
- A Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

### 2. Create Virtual Environment

```bash
cd EnergyBea_assignment
python3 -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set API Key

```bash
cp .env.example .env
# Edit .env and add your Gemini API key:
# GEMINI_API_KEY=your_key_here
```

### 5. Run the App

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## 🧪 Testing

### Test with a sample bill (no API key needed)

```bash
python test_sample.py
```

This creates a synthetic MSEDCL bill image and tests the full Excel generation flow without needing Gemini.

### Test API endpoints

```bash
# Health check
curl http://localhost:5000/api/health

# Upload and extract (replace with your bill file)
curl -X POST http://localhost:5000/api/extract \
  -F "file=@/path/to/bill.pdf"

# Generate Excel from data
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "consumer_name": "Rahul Sharma",
    "consumer_number": "123456789012",
    "billing_period": "Jan 2025 - Feb 2025",
    "units_consumed": 320,
    "sanctioned_load": 5.0,
    "tariff_category": "LT-I Residential",
    "total_bill_amount": 2800,
    "electricity_rate": 8.75
  }'
```

---

## 📊 Excel Output Structure

### Sheet 1: "Bill Data" (Input Sheet)
| Field | Cell | Type |
|-------|------|------|
| Consumer Name | B3 | INPUT |
| Consumer Number | B4 | INPUT |
| Billing Period | B5 | INPUT |
| Units Consumed (kWh) | B6 | **KEY INPUT** |
| Sanctioned Load (kW) | B7 | INPUT |
| Tariff Category | B8 | INPUT |
| Total Bill Amount (₹) | B9 | INPUT |
| Electricity Rate (₹/kWh) | B10 | INPUT |

### Sheet 2: "Solar Calculation" (Formula Sheet — READ ONLY)
| Output | Formula |
|--------|---------|
| Recommended System Size (kW) | `Daily consumption / 5 peak sun hours` |
| Number of Panels | `System kW × 1000 / 540W` |
| Roof Area Required | `Panels × 20 sq ft` |
| Annual Generation (kWh) | `System kW × 5h × 365` |
| Annual Savings (₹) | `Units saved × tariff rate` |
| Govt Subsidy (₹) | `₹30,000/kW up to 2kW, ₹18,000/kW up to 3kW` |
| Net Investment (₹) | `System cost − subsidy` |
| Payback Period (years) | `Net investment / Annual savings` |
| 25-Year ROI (%) | `Compounded savings over 25 years` |
| CO₂ Offset (tonnes/year) | `Generation × 0.82 kg/kWh` |

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | Google Gemini API key from aistudio.google.com |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Web Framework | Flask 3.1 |
| AI Extraction | Google Gemini 2.0 Flash Vision |
| Excel Engine | openpyxl 3.1 |
| Frontend | Vanilla HTML + CSS + JavaScript |
| Environment | python-dotenv |

---

## 🔒 Key Design Decisions

1. **Formula preservation** — `excel_handler.py` checks each cell before writing. If a cell contains a formula (starts with `=`), it is **never overwritten**.
2. **AI-first extraction** — Gemini Vision handles semi-structured bills without any fixed template parsing.
3. **Editable review** — All extracted fields are editable in the UI before Excel generation, preventing bad data from propagating.
4. **Modular services** — `extractor.py` and `excel_handler.py` are independent and testable.

---

## 📝 Notes

- The Excel template is auto-generated on first run if it doesn't exist.
- Uploaded files are stored in `uploads/` (temporary).
- Generated reports are stored in `outputs/` with timestamped filenames.
- Both directories are gitignored.
