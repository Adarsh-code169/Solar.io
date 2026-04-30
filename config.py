"""
Configuration module for Solar Load Calculator.
Loads environment variables and defines app-wide settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ── API Keys ───────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── File Upload Settings ───────────────────────────────────────────────
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp", "bmp", "tiff"}
MAX_FILE_SIZE_MB = 10

# ── Excel Template ─────────────────────────────────────────────────────
TEMPLATE_FILE = TEMPLATE_DIR / "solar_calculator_template.xlsx"

# ── Solar Calculation Defaults ─────────────────────────────────────────
SOLAR_DEFAULTS = {
    "peak_sun_hours": 5.0,           # hours/day (India average)
    "panel_wattage": 540,            # watts per panel
    "cost_per_kw": 55000,            # ₹ per kW installed
    "system_life_years": 25,
    "annual_degradation": 0.005,     # 0.5% per year
    "annual_tariff_increase": 0.05,  # 5% per year
    "co2_per_kwh": 0.82,            # kg CO₂ per kWh (India grid)
}
