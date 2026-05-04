"""
Solar Load Calculator — Flask Application

Main entry point for the web application. Provides API endpoints for:
  - Bill upload and AI extraction
  - Excel report generation and download
  - Template information

Usage:
    python app.py
"""

import io
import os
import logging
import zipfile
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import (
    UPLOAD_DIR, OUTPUT_DIR, STATIC_DIR, TEMPLATE_FILE,
    ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, GEMINI_API_KEY
)
from services.extractor import extract_bill_data
from services.excel_handler import populate_template, get_template_info, create_template
from services.pdf_generator import generate_pdf_proposal

# ── Logging Setup ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Flask App ──────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE_MB * 1024 * 1024


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ══════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Serve the main UI."""
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "gemini_configured": bool(GEMINI_API_KEY),
        "template_exists": TEMPLATE_FILE.exists(),
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/extract", methods=["POST"])
def extract():
    """
    Upload an electricity bill (PDF/image) and extract data using AI.

    Returns JSON with extracted bill fields.
    """
    logger.info("=== EXTRACT REQUEST ===")

    # Validate API key
    if not GEMINI_API_KEY:
        return jsonify({
            "error": "Gemini API key not configured. Set GEMINI_API_KEY in .env file."
        }), 500

    # Validate file upload
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Please select a bill file."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    # Save uploaded file
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_filename = f"{timestamp}_{filename}"
    file_path = UPLOAD_DIR / saved_filename
    file.save(str(file_path))
    logger.info(f"File saved: {file_path} ({file_path.stat().st_size / 1024:.1f} KB)")

    try:
        # Extract data using Gemini AI
        extracted_data = extract_bill_data(str(file_path))

        logger.info(f"Extraction complete: {len(extracted_data)} fields")
        return jsonify({
            "success": True,
            "data": extracted_data,
            "source_file": filename,
        })

    except ValueError as e:
        logger.error(f"Extraction error: {e}")
        return jsonify({"error": str(e)}), 422

    except RuntimeError as e:
        logger.error(f"API error: {e}")
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/generate", methods=["POST"])
def generate():
    """
    Accept extracted/edited data and generate a ZIP containing:
    - Populated Excel solar sizing report
    - Branded PDF proposal (Energybae Solar Proposal)

    Expects JSON body with bill data fields.
    Returns the ZIP file directly as a download.
    """
    logger.info("=== GENERATE REQUEST ===")

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided."}), 400

    try:
        # Generate Excel report
        excel_path = populate_template(data)
        logger.info(f"Excel generated: {Path(excel_path).name}")

        # Generate PDF proposal
        pdf_bytes = generate_pdf_proposal(data)
        logger.info(f"PDF generated: {len(pdf_bytes)} bytes")

        # Pack both into an in-memory ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(excel_path, Path(excel_path).name)
            zf.writestr("Energybae_Solar_Proposal.pdf", pdf_bytes)
        zip_buffer.seek(0)

        logger.info("ZIP package ready for download")
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name="Energybae_Solar_Proposal.zip",
            mimetype="application/zip",
        )

    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        return jsonify({"error": f"Report generation failed: {str(e)}"}), 500


@app.route("/api/download/<filename>", methods=["GET"])
def download(filename):
    """Download a generated Excel file."""
    filename = secure_filename(filename)
    file_path = OUTPUT_DIR / filename

    if not file_path.exists():
        return jsonify({"error": "File not found."}), 404

    logger.info(f"Downloading: {filename}")
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/api/template-info", methods=["GET"])
def template_info():
    """Return information about the Excel template structure."""
    try:
        info = get_template_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Ensure template exists
    if not TEMPLATE_FILE.exists():
        logger.info("Creating Excel template...")
        create_template()

    logger.info("🌞 Solar Load Calculator starting...")
    logger.info(f"   Gemini API: {'✓ Configured' if GEMINI_API_KEY else '✗ NOT SET'}")
    logger.info(f"   Template:   {TEMPLATE_FILE}")
    logger.info(f"   Uploads:    {UPLOAD_DIR}")
    logger.info(f"   Outputs:    {OUTPUT_DIR}")
    logger.info(f"   UI:         http://localhost:5000")

    app.run(debug=True, host="0.0.0.0", port=5001)
