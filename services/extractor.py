"""
AI-powered electricity bill data extractor using Google Gemini Vision API.

Handles both PDF and image inputs. Sends the bill to Gemini with a structured
prompt and returns parsed JSON with all key fields.
"""

import json
import logging
import mimetypes
from pathlib import Path

import google.generativeai as genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# ── Gemini Configuration ───────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)

EXTRACTION_PROMPT = """You are an expert electricity bill data extractor specializing in Indian utility bills.

You will receive a scanned or photographed electricity bill. It may be from any of these utilities:
- MSEDCL (Maharashtra State Electricity Distribution Co. Ltd) — Maharashtra
- Adani Electricity (formerly BSES Rajdhani) — Mumbai
- Tata Power — Mumbai and other regions
- BEST (Brihanmumbai Electric Supply and Transport)
- Any other Indian state electricity board (KSEB, BESCOM, TANGEDCO, etc.)

Extract ALL the following fields. Return ONLY a valid JSON object with no markdown formatting, no code blocks, no extra text.

Required JSON structure:
{
    "consumer_name": "Full name of the consumer/account holder",
    "consumer_number": "Consumer number / Account ID / Service number / BP number",
    "meter_number": "Meter number / Meter serial number if visible",
    "billing_period": "Billing period range (e.g., 'Jan 2025 - Feb 2025')",
    "units_consumed": <kWh units consumed as integer — see aliases below>,
    "sanctioned_load": <sanctioned/connected load in kW as float>,
    "tariff_category": "Tariff category/slab (e.g., 'LT-I Residential', 'Domestic')",
    "total_bill_amount": <total payable amount in rupees as float — look for 'Net Amount', 'Total Amount Payable', 'Amount Due'>,
    "electricity_rate": <average rate per unit in Rs/kWh as float — calculate if not shown>,
    "supply_type": "Single Phase / Three Phase",
    "due_date": "Payment due date if visible",
    "previous_reading": <previous meter reading as integer or null>,
    "current_reading": <current meter reading as integer or null>,
    "additional_info": "Discom name, tariff slab details, or any other useful info"
}

FIELD ALIASES BY UTILITY:

units_consumed — look for any of these labels:
  MSEDCL:        "Units Consumed", "Net Units", "Consumption (kWh)", "EB Units"
  Adani:         "Net Consumption", "Billed Units", "Units (kWh)"
  Tata Power:    "kWh Consumed", "Total Units", "Consumption"
  Generic:       "Units", "kWh", "Electrical Units", "Energy Consumed"
  FALLBACK: If not found directly, compute: current_reading - previous_reading

sanctioned_load — look for:
  "Sanctioned Load", "Connected Load", "Contract Demand", "Contracted Demand", "Load (kW)"

total_bill_amount — look for:
  "Net Amount Payable", "Total Amount", "Amount Due", "Bill Amount", "Payable Amount"
  Use the FINAL total after all charges and taxes. Exclude surcharges listed separately.

electricity_rate — look for:
  "Rate per Unit", "Per Unit Rate", "Energy Charge Rate"
  FALLBACK: Calculate as total_bill_amount / units_consumed

EXTRACTION RULES:
1. Return numbers for numeric fields — never strings like "500 kWh"
2. Strip currency symbols (Rs, ₹), commas, and units (kW, kWh) from numeric values
3. If a field is genuinely absent from the bill, use null
4. For units_consumed, this is the MOST CRITICAL field — try every alias and the meter reading difference before returning null
5. Do NOT confuse slab-wise unit breakdowns with total consumption — extract the TOTAL units
6. For MSEDCL bills with multiple slabs (0-100, 101-300, 301+), sum them or use the printed total
7. Return ONLY the JSON object, nothing else, no explanation
"""


def _repair_json(s: str) -> str:
    """Attempts to fix truncated JSON strings by closing open braces."""
    s = s.strip()
    if not s.startswith('{'):
        return s
    if s.endswith(','):
        s = s[:-1]
    open_braces = s.count('{')
    close_braces = s.count('}')
    while open_braces > close_braces:
        s += '}'
        close_braces += 1
    return s


def extract_bill_data(file_path: str) -> dict:
    """
    Extract electricity bill data from a PDF or image file using Gemini Vision.

    Args:
        file_path: Path to the uploaded bill file (PDF, PNG, JPG, etc.)

    Returns:
        dict: Extracted bill data with all key fields

    Raises:
        ValueError: If file format is unsupported or extraction fails
        RuntimeError: If Gemini API call fails
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    logger.info(f"Extracting data from: {file_path.name}")

    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        suffix = file_path.suffix.lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
        }
        mime_type = mime_map.get(suffix)
        if mime_type is None:
            raise ValueError(f"Unsupported file format: {suffix}")

    logger.info(f"File MIME type: {mime_type}")

    # Upload file to Gemini once (outside retry loop to avoid re-uploading)
    uploaded_file = genai.upload_file(str(file_path), mime_type=mime_type)
    logger.info(f"File uploaded to Gemini: {uploaded_file.name}")

    max_retries = 2
    last_error = None

    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel("gemini-flash-latest")
            response = model.generate_content(
                [EXTRACTION_PROMPT, uploaded_file],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                ),
            )

            raw_text = response.text.strip()
            logger.info(f"Gemini raw response length: {len(raw_text)} chars")

            try:
                extracted_data = json.loads(raw_text)
            except json.JSONDecodeError:
                logger.warning("JSONDecodeError — attempting JSON repair...")
                repaired_text = _repair_json(raw_text)
                extracted_data = json.loads(repaired_text)
                logger.info("JSON repair successful")

            logger.info(f"Successfully extracted {len(extracted_data)} fields")
            return _validate_and_clean(extracted_data)

        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            continue

    logger.error(f"All {max_retries} attempts failed. Last error: {last_error}")
    raise RuntimeError(f"AI extraction failed: {str(last_error)}")


def _validate_and_clean(data: dict) -> dict:
    """
    Validate and clean extracted data, ensuring types are correct and
    applying fallback calculations where fields are missing.
    """
    # ── 1. Cast numeric fields ─────────────────────────────────────────
    numeric_fields = [
        "units_consumed",
        "sanctioned_load",
        "total_bill_amount",
        "electricity_rate",
        "previous_reading",
        "current_reading",
    ]

    for field in numeric_fields:
        value = data.get(field)
        if value is not None and not isinstance(value, (int, float)):
            try:
                cleaned = (
                    str(value)
                    .replace(",", "")
                    .replace("₹", "")
                    .replace("Rs", "")
                    .replace("rs", "")
                    .replace("kWh", "")
                    .replace("kW", "")
                    .strip()
                )
                data[field] = float(cleaned)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert {field}='{value}' to number, setting to null")
                data[field] = None

    # ── 2. Fallback: calculate units_consumed from meter readings ──────
    if data.get("units_consumed") is None:
        prev = data.get("previous_reading")
        curr = data.get("current_reading")
        if (
            prev is not None
            and curr is not None
            and isinstance(prev, (int, float))
            and isinstance(curr, (int, float))
            and curr > prev
        ):
            data["units_consumed"] = int(curr - prev)
            logger.info(f"Calculated units_consumed from meter readings: {data['units_consumed']}")

    # ── 3. Fallback: calculate electricity_rate from bill and units ────
    if data.get("electricity_rate") is None:
        bill_amount = data.get("total_bill_amount")
        units = data.get("units_consumed")
        if bill_amount and units and units > 0:
            data["electricity_rate"] = round(bill_amount / units, 2)
            logger.info(f"Calculated electricity_rate: Rs{data['electricity_rate']}/kWh")

    # ── 4. Type enforcement and range validation ───────────────────────
    if data.get("units_consumed") is not None:
        data["units_consumed"] = max(0, int(data["units_consumed"]))

    if data.get("total_bill_amount") is not None:
        data["total_bill_amount"] = max(0.0, float(data["total_bill_amount"]))

    if data.get("sanctioned_load") is not None:
        load = float(data["sanctioned_load"])
        # Clamp to physically reasonable range (0.5 kW – 200 kW)
        data["sanctioned_load"] = round(max(0.5, min(200.0, load)), 3)

    if data.get("electricity_rate") is not None:
        data["electricity_rate"] = round(float(data["electricity_rate"]), 2)

    # ── 5. Strip whitespace from string fields ─────────────────────────
    string_fields = [
        "consumer_name", "consumer_number", "meter_number",
        "billing_period", "tariff_category", "supply_type",
        "due_date", "additional_info",
    ]
    for field in string_fields:
        val = data.get(field)
        if isinstance(val, str):
            data[field] = val.strip() or None

    return data
