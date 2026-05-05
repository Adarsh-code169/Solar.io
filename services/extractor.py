"""
AI-powered electricity bill data extractor using Google Gemini Vision API.

Accuracy improvements over v1:
- Extracts energy_charges, fixed_charges, taxes separately for correct rate math
- electricity_rate = energy_charges / units  (not total_bill / units which is inflated)
- Cross-validation: rate × units must roughly equal energy_charges, else recalculate
- Explicit MSEDCL slab summation instructions
- Realistic range guards: rate ₹1.5–₹18, load 0.5–200 kW, units > 0
- Gemini response schema enforces correct types, eliminates string-for-number errors
"""

import json
import logging
import mimetypes
from pathlib import Path

import google.generativeai as genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

# ─────────────────────────────────────────────────────────────────────────────
# EXTRACTION PROMPT
# ─────────────────────────────────────────────────────────────────────────────
EXTRACTION_PROMPT = """You are an expert Indian electricity bill analyst. Your job is to extract data from the bill with maximum accuracy.

Supported utilities: MSEDCL, Adani Electricity, Tata Power, BEST, KSEB, BESCOM, TANGEDCO, and all Indian state electricity boards.

Return ONLY a valid JSON object — no markdown, no code block, no explanation, nothing else.

━━━ REQUIRED JSON FIELDS ━━━

{
    "consumer_name":      "Full name exactly as printed on the bill",
    "consumer_number":    "Consumer / Account / Service / BP number",
    "meter_number":       "Meter serial number, or null if not printed",
    "billing_period":     "e.g. 'March 2026' or 'Feb 2026 - Mar 2026'",
    "previous_reading":   <integer meter reading, or null>,
    "current_reading":    <integer meter reading, or null>,
    "units_consumed":     <integer — TOTAL kWh billed — READ RULE 1 CAREFULLY>,
    "sanctioned_load":    <float kW — READ RULE 2>,
    "tariff_category":    "e.g. 'LT-II Domestic', 'Residential', 'Commercial'",
    "supply_type":        "Single Phase or Three Phase",
    "energy_charges":     <float ₹ — ONLY the variable per-unit consumption charge — READ RULE 3>,
    "fixed_charges":      <float ₹ — meter rent + connection charge + demand charge, or null>,
    "taxes_and_duties":   <float ₹ — GST + electricity duty + surcharges total, or null>,
    "total_bill_amount":  <float ₹ — FINAL net payable — READ RULE 4>,
    "electricity_rate":   <float ₹/kWh — READ RULE 5>,
    "due_date":           "DD-MMM-YYYY or as printed, or null",
    "additional_info":    "Discom name, division, tariff slab info, or any key notes"
}

━━━ RULE 1 — units_consumed (MOST CRITICAL) ━━━
Indian bills often show slab-wise breakdown. You MUST return the TOTAL, not one slab.

MSEDCL example — bill shows:
  0–100 units    →  100 units
  101–300 units  →  200 units
  301–560 units  →  260 units
CORRECT answer: 560   ✓
WRONG answer: 260 or 100   ✗

Priority order:
  1. Look for a printed "Total Units", "Net Units", "Units Consumed", "Billed Units" — use that directly
  2. If only slab-wise shown, SUM all the slab unit values
  3. FALLBACK: current_reading − previous_reading
  4. Return as INTEGER (no decimal point, no "kWh")

━━━ RULE 2 — sanctioned_load ━━━
Look for: "Sanctioned Load", "Connected Load", "Contract Demand"
⚠️ Return in kW. If the bill shows Watts (e.g. 1500W), divide by 1000 → 1.5

━━━ RULE 3 — energy_charges (KEY FOR ACCURATE RATE) ━━━
This is ONLY the portion of the bill that changes based on how many units you consume.
It does NOT include: fixed charges, meter rent, wheeling charges, taxes, duties, subsidies.

Look for labels: "Energy Charges", "Variable Charges", "Consumption Charges", "Unit Charges"

For MSEDCL: Sum the slab-wise energy charges (each slab has a ₹ amount — add them all)
If you cannot find this separately, return null — do NOT guess.

━━━ RULE 4 — total_bill_amount ━━━
Use the FINAL amount the customer must pay. This is usually:
  - Boxed or highlighted at the bottom
  - Labeled "Net Amount Payable", "Total Amount Due", "Amount Payable", "Net Payable"

Do NOT use:
  - "Current Month Charges" (excludes arrears)
  - "Gross Amount" (before subsidy/rebate)
  - Any intermediate subtotal

━━━ RULE 5 — electricity_rate ━━━
This is the effective variable cost per unit in ₹/kWh.

PRIORITY ORDER — use the first one that is possible:
  1. DIRECT: Bill explicitly prints a "Rate per Unit" or "Energy Charge Rate" → use that
  2. CALCULATED: energy_charges ÷ units_consumed  ← MOST ACCURATE METHOD
  3. ESTIMATED: (total_bill_amount − fixed_charges − taxes_and_duties) ÷ units_consumed
  4. LAST RESORT: total_bill_amount ÷ units_consumed  ← least accurate, includes all charges

⚠️ Valid range for Indian residential/commercial bills: ₹1.50 to ₹18.00 per unit
If your calculation falls outside this range, you have the wrong inputs — re-check.
Round to 2 decimal places.

━━━ FIELD ALIASES BY UTILITY ━━━

units_consumed:
  MSEDCL    → "Units Consumed", "Net Units", "EB Units", "Consumption (kWh)"
  Adani     → "Net Consumption", "Billed Units", "Units (kWh)"
  Tata Power→ "kWh Consumed", "Total Units"
  Generic   → "Units", "kWh", "Energy Consumed", "Electrical Units"

total_bill_amount:
  MSEDCL    → "Net Amount Payable", "Net Payable Amount"
  Adani     → "Total Amount Due", "Amount Payable"
  Tata Power→ "Net Bill Amount", "Total Payable"
  Generic   → "Bill Amount", "Amount Due", "Payable Amount"

━━━ ABSOLUTE RULES ━━━
1. Never return a number as a string — "560" is WRONG, 560 is CORRECT
2. Strip ₹, Rs, commas, kW, kWh from all numeric values before returning
3. If a field is genuinely not present on the bill, return null — do not guess
4. Return ONLY the JSON object — no extra text, no markdown, no code fences
"""


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI RESPONSE SCHEMA  — forces correct types, eliminates string-for-number
# ─────────────────────────────────────────────────────────────────────────────
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "consumer_name":    {"type": "string"},
        "consumer_number":  {"type": "string"},
        "meter_number":     {"type": "string"},
        "billing_period":   {"type": "string"},
        "previous_reading": {"type": "number"},
        "current_reading":  {"type": "number"},
        "units_consumed":   {"type": "number"},
        "sanctioned_load":  {"type": "number"},
        "tariff_category":  {"type": "string"},
        "supply_type":      {"type": "string"},
        "energy_charges":   {"type": "number"},
        "fixed_charges":    {"type": "number"},
        "taxes_and_duties": {"type": "number"},
        "total_bill_amount":{"type": "number"},
        "electricity_rate": {"type": "number"},
        "due_date":         {"type": "string"},
        "additional_info":  {"type": "string"},
    },
}


def _strip_numeric(value) -> float | None:
    """Strip currency/unit symbols and cast to float. Returns None on failure."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = (
            str(value)
            .replace(",", "")
            .replace("₹", "")
            .replace("Rs", "")
            .replace("rs", "")
            .replace("RS", "")
            .replace("kWh", "")
            .replace("kW", "")
            .replace("KW", "")
            .strip()
        )
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _repair_json(s: str) -> str:
    """Close unclosed JSON braces from truncated Gemini output."""
    s = s.strip()
    if not s.startswith("{"):
        return s
    if s.endswith(","):
        s = s[:-1]
    open_b  = s.count("{")
    close_b = s.count("}")
    while open_b > close_b:
        s += "}"
        close_b += 1
    return s


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXTRACTION FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def extract_bill_data(file_path: str) -> dict:
    """
    Extract electricity bill data from a PDF or image using Gemini Vision.
    Returns a cleaned, validated dict with accurate field values.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise ValueError(f"File not found: {file_path}")

    logger.info(f"Extracting: {file_path.name}")

    # Resolve MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        mime_map = {
            ".pdf":  "application/pdf",
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".bmp":  "image/bmp",
            ".tiff": "image/tiff",
        }
        mime_type = mime_map.get(file_path.suffix.lower())
        if mime_type is None:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

    # Upload once — reuse across retries
    uploaded_file = genai.upload_file(str(file_path), mime_type=mime_type)
    logger.info(f"Uploaded to Gemini: {uploaded_file.name}")

    last_error = None
    for attempt in range(3):
        try:
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(
                [EXTRACTION_PROMPT, uploaded_file],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                ),
            )

            raw = response.text.strip()
            logger.info(f"Gemini response ({len(raw)} chars), attempt {attempt + 1}")

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("JSONDecodeError — attempting repair...")
                data = json.loads(_repair_json(raw))
                logger.info("JSON repair successful")

            return _validate_and_clean(data)

        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1}/3 failed: {e}")

    raise RuntimeError(f"AI extraction failed after 3 attempts: {last_error}")


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION & ACCURACY CORRECTION
# ─────────────────────────────────────────────────────────────────────────────

def _validate_and_clean(data: dict) -> dict:
    """
    Post-process Gemini output:
      1. Cast all numeric fields robustly
      2. Fallback: units from meter readings
      3. Accurate rate calculation (energy_charges ÷ units, not total ÷ units)
      4. Cross-validate rate × units ≈ energy_charges; recompute if drifted
      5. Range guards with logging
      6. Strip whitespace from string fields
    """

    # ── Step 1: Cast all numeric fields ───────────────────────────────────
    numeric_fields = [
        "units_consumed", "sanctioned_load", "total_bill_amount",
        "electricity_rate", "previous_reading", "current_reading",
        "energy_charges", "fixed_charges", "taxes_and_duties",
    ]
    for field in numeric_fields:
        raw = data.get(field)
        cleaned = _strip_numeric(raw)
        if cleaned is None and raw is not None:
            logger.warning(f"Could not parse {field}='{raw}' — set to null")
        data[field] = cleaned

    # ── Step 2: Fallback units from meter readings ─────────────────────────
    if not data.get("units_consumed"):
        prev = data.get("previous_reading")
        curr = data.get("current_reading")
        if prev is not None and curr is not None and curr > prev:
            data["units_consumed"] = int(curr - prev)
            logger.info(f"[FALLBACK] units_consumed = {data['units_consumed']} (from readings)")

    # ── Step 3: Cross-validate units vs meter readings ─────────────────────
    units = data.get("units_consumed")
    prev  = data.get("previous_reading")
    curr  = data.get("current_reading")
    if units and prev is not None and curr is not None and curr > prev:
        reading_diff = int(curr - prev)
        tolerance = max(10, reading_diff * 0.10)   # 10% tolerance
        if abs(units - reading_diff) > tolerance:
            logger.warning(
                f"units_consumed={units} differs from meter diff={reading_diff} "
                f"by more than 10% — trusting meter readings"
            )
            data["units_consumed"] = reading_diff

    # ── Step 4: Accurate electricity_rate calculation ──────────────────────
    units          = data.get("units_consumed") or 0
    energy_chg     = data.get("energy_charges")
    fixed_chg      = data.get("fixed_charges") or 0
    taxes          = data.get("taxes_and_duties") or 0
    total          = data.get("total_bill_amount") or 0
    extracted_rate = data.get("electricity_rate")

    computed_rate = None
    rate_method   = None

    if units > 0:
        if energy_chg and energy_chg > 0:
            # Method 1 — best: energy charges ÷ units (excludes fixed & taxes)
            computed_rate = round(energy_chg / units, 2)
            rate_method   = "energy_charges / units"

        elif total > 0:
            # Method 2 — deduct known fixed components
            variable_part = total - fixed_chg - taxes
            if variable_part > 0:
                computed_rate = round(variable_part / units, 2)
                rate_method   = "(total - fixed - taxes) / units"
            else:
                # Method 3 — last resort: total ÷ units (overestimates)
                computed_rate = round(total / units, 2)
                rate_method   = "total / units [approximate]"

    # Decide which rate to use
    if computed_rate is not None:
        if extracted_rate is not None:
            # Prefer the more accurate computed rate unless extracted is very close
            diff_pct = abs(computed_rate - extracted_rate) / max(computed_rate, 0.01)
            if diff_pct > 0.20:   # >20% discrepancy → trust our math
                logger.info(
                    f"Rate discrepancy: extracted={extracted_rate}, "
                    f"computed={computed_rate} ({rate_method}) — using computed"
                )
                data["electricity_rate"] = computed_rate
            else:
                # Extracted and computed agree — keep extracted (directly from bill)
                data["electricity_rate"] = round(extracted_rate, 2)
                logger.info(f"Rate confirmed: {data['electricity_rate']} ₹/kWh")
        else:
            data["electricity_rate"] = computed_rate
            logger.info(f"Rate set via {rate_method}: {computed_rate} ₹/kWh")
    elif extracted_rate is not None:
        data["electricity_rate"] = round(extracted_rate, 2)

    # ── Step 5: Cross-validate rate × units ≈ energy component ───────────
    final_rate = data.get("electricity_rate")
    if final_rate and units > 0 and energy_chg and energy_chg > 0:
        implied_energy = final_rate * units
        diff_pct = abs(implied_energy - energy_chg) / energy_chg
        if diff_pct > 0.25:   # >25% off
            corrected = round(energy_chg / units, 2)
            logger.warning(
                f"Rate × units (₹{implied_energy:.0f}) differs from energy_charges "
                f"(₹{energy_chg:.0f}) by {diff_pct:.0%} — correcting rate to {corrected}"
            )
            data["electricity_rate"] = corrected

    # ── Step 6: Range guards ───────────────────────────────────────────────
    if data.get("units_consumed") is not None:
        data["units_consumed"] = max(0, int(data["units_consumed"]))

    if data.get("total_bill_amount") is not None:
        data["total_bill_amount"] = max(0.0, round(float(data["total_bill_amount"]), 2))

    if data.get("sanctioned_load") is not None:
        load = float(data["sanctioned_load"])
        if load > 1000:                    # probably in Watts — convert
            load = load / 1000
            logger.info(f"sanctioned_load converted from W to kW: {load}")
        data["sanctioned_load"] = round(max(0.5, min(200.0, load)), 3)

    if data.get("electricity_rate") is not None:
        rate = float(data["electricity_rate"])
        # Hard clamp: Indian residential/commercial realistic range
        if rate < 1.5 or rate > 18.0:
            logger.warning(f"electricity_rate={rate} outside realistic range [1.5–18] — recalculating")
            if units > 0 and energy_chg and energy_chg > 0:
                data["electricity_rate"] = round(energy_chg / units, 2)
            elif units > 0 and total > 0:
                data["electricity_rate"] = round(total / units, 2)
            else:
                data["electricity_rate"] = None
            logger.info(f"Rate after clamp correction: {data['electricity_rate']}")
        else:
            data["electricity_rate"] = round(rate, 2)

    if data.get("energy_charges") is not None:
        data["energy_charges"] = round(max(0.0, float(data["energy_charges"])), 2)

    if data.get("fixed_charges") is not None:
        data["fixed_charges"] = round(max(0.0, float(data["fixed_charges"])), 2)

    if data.get("taxes_and_duties") is not None:
        data["taxes_and_duties"] = round(max(0.0, float(data["taxes_and_duties"])), 2)

    # ── Step 7: String field cleanup ───────────────────────────────────────
    string_fields = [
        "consumer_name", "consumer_number", "meter_number",
        "billing_period", "tariff_category", "supply_type",
        "due_date", "additional_info",
    ]
    for field in string_fields:
        val = data.get(field)
        if isinstance(val, str):
            data[field] = val.strip() or None

    # ── Step 8: Sanity log ─────────────────────────────────────────────────
    logger.info(
        f"Final values — units={data.get('units_consumed')} kWh | "
        f"rate=₹{data.get('electricity_rate')}/kWh | "
        f"bill=₹{data.get('total_bill_amount')} | "
        f"energy_chg=₹{data.get('energy_charges')} | "
        f"load={data.get('sanctioned_load')} kW"
    )

    return data
