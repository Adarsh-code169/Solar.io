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

EXTRACTION_PROMPT = """You are an expert electricity bill data extractor for Indian electricity bills (especially MSEDCL Maharashtra bills).

Analyze this electricity bill image/document carefully and extract ALL the following fields. Return ONLY a valid JSON object with no markdown formatting, no code blocks, no extra text.

Required JSON structure:
{
    "consumer_name": "Full name of the consumer/account holder",
    "consumer_number": "Consumer number / Account ID",
    "meter_number": "Meter number if visible",
    "billing_period": "Billing period (e.g., 'Jan 2025 - Feb 2025')",
    "units_consumed": <number of kWh units consumed as integer>,
    "sanctioned_load": <sanctioned/connected load in kW as float>,
    "tariff_category": "Tariff category/slab (e.g., 'LT-I Residential')",
    "total_bill_amount": <total bill amount in rupees as float>,
    "electricity_rate": <average rate per unit in ₹/kWh as float>,
    "supply_type": "Single Phase / Three Phase",
    "due_date": "Payment due date if visible",
    "previous_reading": <previous meter reading as integer or null>,
    "current_reading": <current meter reading as integer or null>,
    "additional_info": "Any other relevant information from the bill"
}

IMPORTANT RULES:
1. Extract EXACT values as printed on the bill
2. For numeric fields, return numbers (not strings)
3. If a field is not found, use null
4. For units_consumed, this is the MOST CRITICAL field - look for "Units Consumed", "Consumption", "kWh", or calculate from meter readings
5. For electricity_rate, calculate as total_bill_amount / units_consumed if not explicitly shown
6. For sanctioned_load, look for "Connected Load", "Sanctioned Load", "Contract Demand"
7. Return ONLY the JSON object, nothing else
"""


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

    try:
        # Upload file to Gemini
        uploaded_file = genai.upload_file(str(file_path), mime_type=mime_type)
        logger.info(f"File uploaded to Gemini: {uploaded_file.name}")

    def repair_json(s):
        """Attempts to fix truncated JSON strings."""
        s = s.strip()
        if not s.startswith('{'): return s
        # Count braces
        open_braces = s.count('{')
        close_braces = s.count('}')
        
        # If truncated mid-key or mid-value
        if s.endswith(','): s = s[:-1]
        
        # Add missing closing braces
        while open_braces > close_braces:
            s += '}'
            close_braces += 1
        return s

    max_retries = 2
    for attempt in range(max_retries):
        try:
            # Initialize model and generate response
            model = genai.GenerativeModel("gemini-flash-latest")
            response = model.generate_content(
                [EXTRACTION_PROMPT, uploaded_file],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0, # Zero temperature for max consistency
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                ),
            )

            raw_text = response.text.strip()
            logger.info(f"Gemini raw response length: {len(raw_text)} chars")

            try:
                extracted_data = json.loads(raw_text)
            except json.JSONDecodeError:
                # Try to repair the JSON if it's truncated
                repaired_text = repair_json(raw_text)
                extracted_data = json.loads(repaired_text)
                logger.warning("Repaired truncated JSON response")

            logger.info(f"Successfully extracted {len(extracted_data)} fields")
            return _validate_and_clean(extracted_data)

        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Final attempt failed: {e}")
                raise RuntimeError(f"AI extraction failed after {max_retries} attempts: {str(e)}")
            logger.warning(f"Attempt {attempt + 1} failed, retrying... Error: {e}")
            continue


def _validate_and_clean(data: dict) -> dict:
    """
    Validate and clean extracted data, ensuring types are correct.
    """
    # Ensure numeric fields are actually numbers
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
                # Try to parse string to number (remove commas, ₹ symbol, etc.)
                cleaned = str(value).replace(",", "").replace("₹", "").replace("Rs", "").strip()
                data[field] = float(cleaned)
            except (ValueError, TypeError):
                logger.warning(f"Could not convert {field}='{value}' to number, setting to null")
                data[field] = None

    # Calculate electricity rate if missing but we have bill amount and units
    if data.get("electricity_rate") is None:
        bill_amount = data.get("total_bill_amount")
        units = data.get("units_consumed")
        if bill_amount and units and units > 0:
            data["electricity_rate"] = round(bill_amount / units, 2)
            logger.info(f"Calculated electricity_rate: ₹{data['electricity_rate']}/kWh")

    # Ensure units_consumed is an integer
    if data.get("units_consumed") is not None:
        data["units_consumed"] = int(data["units_consumed"])

    return data
