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
    "peak_sun_hours": 4.5,           # hours/day — conservative India average (was 5.0, overstated yield)
    "performance_ratio": 0.75,       # system efficiency: inverter + cable + dust + temp derating
    "growth_buffer": 1.20,           # 20% oversize for degradation, cloudy days, future load growth
    "panel_wattage": 400,            # watts per panel (standard residential/commercial)
    "cost_per_kw": 55000,            # ₹ per kW installed (all-in)
    "system_life_years": 25,
    "annual_degradation": 0.005,     # 0.5% per year panel efficiency loss
    "annual_tariff_increase": 0.05,  # 5% per year tariff escalation
    "co2_per_kwh": 0.82,            # kg CO₂ per kWh (India grid emission factor)
}
