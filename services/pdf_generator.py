"""
Branded PDF proposal generator for Energybae solar proposals.

Produces a 3-page ReportLab PDF:
  Page 1 — Cover (company branding, customer name, date)
  Page 2 — System Sizing & Technical Specifications
  Page 3 — Financial ROI & Savings Analysis
"""

import io
import math
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ── Brand colours ──────────────────────────────────────────────────────
BLUE       = colors.HexColor("#2563eb")
BLUE_DARK  = colors.HexColor("#1d4ed8")
BLUE_LIGHT = colors.HexColor("#eff6ff")
EMERALD    = colors.HexColor("#10b981")
EMERALD_DK = colors.HexColor("#059669")
SLATE      = colors.HexColor("#0f172a")
SLATE_MID  = colors.HexColor("#475569")
SLATE_LITE = colors.HexColor("#94a3b8")
WHITE      = colors.white
GREY_BG    = colors.HexColor("#f8fafc")
BORDER     = colors.HexColor("#e2e8f0")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm


# ══════════════════════════════════════════════════════════════════════
# Sizing & Financial helpers
# ══════════════════════════════════════════════════════════════════════

def _compute_sizing(data: dict) -> dict:
    units        = float(data.get("units_consumed") or 0)
    rate         = float(data.get("electricity_rate") or 0)
    bill         = float(data.get("total_bill_amount") or 0)
    supply       = data.get("supply_type") or "Single Phase"
    tariff       = data.get("tariff_category") or "Residential"

    # Use bill amount as baseline if rate is missing
    if rate == 0 and units > 0:
        rate = round(bill / units, 2)

    # Industry-standard sizing formula:
    #   Monthly yield per kW = peak_sun_hours × 30 days × performance_ratio
    #                        = 4.5h × 30 × 0.75 = 101.25 kWh/kW/month
    #   +20 % buffer for degradation, cloudy days, and future load growth
    PEAK_SUN_HOURS     = 4.5
    PERFORMANCE_RATIO  = 0.75
    GROWTH_BUFFER      = 1.20
    monthly_yield_per_kw = PEAK_SUN_HOURS * 30 * PERFORMANCE_RATIO   # 101.25

    recommended_kw    = math.ceil((units / monthly_yield_per_kw) * GROWTH_BUFFER) if units > 0 else 0
    panel_count       = math.ceil(recommended_kw * 1000 / 400) if recommended_kw > 0 else 0
    roof_area_sqft    = recommended_kw * 100
    system_cost       = recommended_kw * 55_000

    annual_savings_y1 = units * rate * 12 * 0.90
    payback_years     = round(system_cost / annual_savings_y1, 1) if annual_savings_y1 > 0 else 0

    # 25-year cumulative savings with 3 % annual rate escalation
    savings_25yr_gross = sum(annual_savings_y1 * (1.03 ** k) for k in range(25))
    savings_25yr_net   = savings_25yr_gross - system_cost

    return {
        "units":             units,
        "rate":              rate,
        "recommended_kw":    recommended_kw,
        "panel_count":       panel_count,
        "roof_area_sqft":    roof_area_sqft,
        "system_cost":       system_cost,
        "annual_savings_y1": annual_savings_y1,
        "payback_years":     payback_years,
        "savings_25yr_net":  savings_25yr_net,
        "supply":            supply,
        "tariff":            tariff,
    }


def _fmt_inr(value: float) -> str:
    """Format a number as Indian rupees with comma grouping."""
    if value >= 1_00_00_000:
        return f"₹{value / 1_00_00_000:.2f} Cr"
    if value >= 1_00_000:
        return f"₹{value / 1_00_000:.2f} L"
    return f"₹{int(round(value)):,}"


# ══════════════════════════════════════════════════════════════════════
# Page templates (cover vs. inner pages)
# ══════════════════════════════════════════════════════════════════════

def _cover_bg(canvas, doc):
    """Draw the cover page blue background and decorative elements."""
    canvas.saveState()

    # Full-page gradient-like blue background (two overlapping rects)
    canvas.setFillColor(BLUE_DARK)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    canvas.setFillColor(BLUE)
    canvas.rect(0, PAGE_H * 0.35, PAGE_W, PAGE_H * 0.65, fill=1, stroke=0)

    # Bottom white content panel
    panel_h = PAGE_H * 0.38
    canvas.setFillColor(WHITE)
    canvas.roundRect(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, panel_h, 12, fill=1, stroke=0)

    # Decorative circle (top-right)
    canvas.setFillColor(colors.HexColor("#1e40af"))
    canvas.circle(PAGE_W + 20, PAGE_H + 20, 90, fill=1, stroke=0)

    canvas.restoreState()


def _inner_bg(canvas, doc):
    """Draw the inner page header bar."""
    canvas.saveState()

    # Top accent bar
    canvas.setFillColor(BLUE)
    canvas.rect(0, PAGE_H - 18 * mm, PAGE_W, 18 * mm, fill=1, stroke=0)

    # Header text
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(MARGIN, PAGE_H - 11 * mm, "ENERGYBAE  |  Solar System Proposal")

    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 11 * mm,
                           f"Page {doc.page} of 3")

    # Bottom footer
    canvas.setFillColor(BLUE)
    canvas.rect(0, 0, PAGE_W, 10 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(PAGE_W / 2, 3.5 * mm,
                             "Energybae — Empowering India with Clean Solar Energy  |  www.energybae.in")

    canvas.restoreState()


# ══════════════════════════════════════════════════════════════════════
# Style helpers
# ══════════════════════════════════════════════════════════════════════

def _styles():
    base = getSampleStyleSheet()

    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "cover_company": s("cco",
            fontName="Helvetica-Bold", fontSize=13,
            textColor=colors.HexColor("#93c5fd"), alignment=TA_CENTER),

        "cover_title": s("cti",
            fontName="Helvetica-Bold", fontSize=32,
            textColor=WHITE, alignment=TA_CENTER, spaceAfter=6),

        "cover_sub": s("csu",
            fontName="Helvetica", fontSize=14,
            textColor=colors.HexColor("#bfdbfe"), alignment=TA_CENTER),

        "cover_panel_name": s("cpn",
            fontName="Helvetica-Bold", fontSize=18,
            textColor=SLATE, alignment=TA_CENTER, spaceAfter=4),

        "cover_panel_meta": s("cpm",
            fontName="Helvetica", fontSize=11,
            textColor=SLATE_MID, alignment=TA_CENTER),

        "section_title": s("sti",
            fontName="Helvetica-Bold", fontSize=16,
            textColor=BLUE, spaceAfter=4),

        "section_sub": s("ssu",
            fontName="Helvetica", fontSize=10,
            textColor=SLATE_MID, spaceAfter=16),

        "table_header": s("thr",
            fontName="Helvetica-Bold", fontSize=10,
            textColor=WHITE, alignment=TA_LEFT),

        "table_cell": s("tce",
            fontName="Helvetica", fontSize=10,
            textColor=SLATE),

        "table_cell_bold": s("tcb",
            fontName="Helvetica-Bold", fontSize=10,
            textColor=SLATE),

        "note": s("nte",
            fontName="Helvetica-Oblique", fontSize=8,
            textColor=SLATE_LITE, spaceAfter=0),

        "highlight_label": s("hla",
            fontName="Helvetica", fontSize=10,
            textColor=SLATE_MID),

        "highlight_value": s("hlv",
            fontName="Helvetica-Bold", fontSize=22,
            textColor=EMERALD),
    }


def _table_style(header_color=BLUE, alt_color=GREY_BG):
    return TableStyle([
        # Header row
        ("BACKGROUND",   (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR",    (0, 0), (-1, 0), WHITE),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING",(0, 0), (-1, 0), 10),
        ("TOPPADDING",   (0, 0), (-1, 0), 10),
        # Data rows
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 10),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, alt_color]),
        ("TOPPADDING",   (0, 1), (-1, -1), 9),
        ("BOTTOMPADDING",(0, 1), (-1, -1), 9),
        ("LEFTPADDING",  (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        # Grid
        ("GRID",         (0, 0), (-1, -1), 0.5, BORDER),
        ("ROUNDEDCORNERS", [6]),
    ])


# ══════════════════════════════════════════════════════════════════════
# Page builders
# ══════════════════════════════════════════════════════════════════════

def _build_cover(data: dict, st: dict) -> list:
    customer = data.get("consumer_name") or "Valued Customer"
    consumer_no = data.get("consumer_number") or "—"
    billing_period = data.get("billing_period") or "—"
    today = date.today().strftime("%d %B %Y")

    story = []

    # ── Upper blue area content (positioned via Spacers) ──
    story.append(Spacer(1, 70 * mm))
    story.append(Paragraph("ENERGYBAE", st["cover_company"]))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Solar System Proposal", st["cover_title"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Customised for your energy needs", st["cover_sub"]))

    # ── White bottom panel content ──────────────────────────────────────
    # Spacer to push content into the white panel area
    story.append(Spacer(1, 28 * mm))

    story.append(Paragraph(customer, st["cover_panel_name"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(f"Consumer No: {consumer_no}", st["cover_panel_meta"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"Billing Period: {billing_period}", st["cover_panel_meta"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"Prepared on: {today}", st["cover_panel_meta"]))

    return story


def _build_sizing(data: dict, sz: dict, st: dict) -> list:
    story = []
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("System Sizing & Technical Specifications", st["section_title"]))
    story.append(Paragraph(
        "Recommended solar system parameters based on your monthly consumption.",
        st["section_sub"]
    ))

    table_data = [
        ["Parameter", "Value"],
        ["Monthly Consumption",          f"{int(sz['units'])} kWh"],
        ["Recommended System Size",      f"{sz['recommended_kw']} kW"],
        ["Estimated Panel Count",        f"{sz['panel_count']} panels  (400 W each)"],
        ["Roof Area Required",           f"{sz['roof_area_sqft']:,} sq ft"],
        ["Units Generated / Month",      f"{sz['recommended_kw'] * 120:,} kWh (estimated)"],
        ["Grid Supply Type",             sz["supply"]],
        ["Tariff Category",              sz["tariff"]],
        ["Average Electricity Rate",     f"₹{sz['rate']:.2f} / kWh"],
    ]

    col_widths = [(PAGE_W - 2 * MARGIN) * f for f in [0.52, 0.48]]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(_table_style())
    story.append(t)

    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(
        "Assumptions: 1 kW system generates ~120 kWh/month under average Indian irradiance. "
        "400 W monocrystalline panels. Roof area calculated at 100 sq ft per kW.",
        st["note"]
    ))

    return story


def _build_roi(sz: dict, st: dict) -> list:
    story = []
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Financial ROI & Savings Analysis", st["section_title"]))
    story.append(Paragraph(
        "25-year projection assuming 3% annual electricity rate escalation and 90% bill reduction after solar.",
        st["section_sub"]
    ))

    roi_data = [
        ["Item", "Value"],
        ["Estimated System Cost",         _fmt_inr(sz["system_cost"])],
        ["Annual Bill Savings (Year 1)",  _fmt_inr(sz["annual_savings_y1"])],
        ["Payback Period",                f"{sz['payback_years']} years"],
        ["25-Year Net Savings",           _fmt_inr(sz["savings_25yr_net"])],
        ["CO₂ Offset (25 yrs, approx.)", f"{int(sz['recommended_kw'] * 120 * 12 * 25 * 0.82 / 1000)} tonnes"],
    ]

    col_widths = [(PAGE_W - 2 * MARGIN) * f for f in [0.58, 0.42]]
    t = Table(roi_data, colWidths=col_widths, repeatRows=1)

    roi_style = _table_style(header_color=EMERALD_DK)
    # Bold the payback and 25-yr rows
    roi_style.add("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold")
    roi_style.add("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold")
    roi_style.add("TEXTCOLOR", (1, 4), (1, 4), EMERALD_DK)
    t.setStyle(roi_style)
    story.append(t)

    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(
        "Disclaimer: All figures are estimates based on current consumption data and standard solar "
        "industry assumptions. Actual savings may vary based on panel orientation, shading, local "
        "irradiance, and grid tariff changes. System cost is an indicative mid-market estimate at "
        "₹55,000 per kW installed.",
        st["note"]
    ))

    return story


# ══════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════

def generate_pdf_proposal(data: dict) -> bytes:
    """
    Generate a branded 3-page PDF proposal.

    Args:
        data: Extracted bill data dict (consumer_name, units_consumed, etc.)

    Returns:
        Raw PDF bytes ready to be written to a file or ZIP archive.
    """
    buf = io.BytesIO()
    st  = _styles()
    sz  = _compute_sizing(data)

    # ── Document with two page templates ──────────────────────────────
    cover_frame = Frame(
        MARGIN, MARGIN,
        PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN,
        id="cover", showBoundary=0,
    )
    inner_frame = Frame(
        MARGIN, 14 * mm,
        PAGE_W - 2 * MARGIN, PAGE_H - 32 * mm,
        id="inner", showBoundary=0,
    )

    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
        title="Energybae Solar Proposal",
        author="Energybae",
    )
    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=[cover_frame], onPage=_cover_bg),
        PageTemplate(id="Inner", frames=[inner_frame], onPage=_inner_bg),
    ])

    story = []

    # Page 1 — Cover
    story += _build_cover(data, st)

    # Page 2 — System Sizing
    story.append(NextPageTemplate("Inner"))
    story.append(PageBreak())
    story += _build_sizing(data, sz, st)

    # Page 3 — Financial ROI
    story.append(PageBreak())
    story += _build_roi(sz, st)

    doc.build(story)
    return buf.getvalue()
