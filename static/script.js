"use strict";

// ── State ──────────────────────────────────────────────────────
let selectedFile  = null;
let extractedData = {};
let downloadUrl   = "";
let roiChart      = null;

// ── DOM refs ───────────────────────────────────────────────────
const uploadZone     = document.getElementById("upload-zone");
const fileInput      = document.getElementById("file-input");
const filePreview    = document.getElementById("file-preview");
const fileNameEl     = document.getElementById("file-name");
const fileSizeEl     = document.getElementById("file-size");
const btnRemove      = document.getElementById("btn-remove");
const btnExtract     = document.getElementById("btn-extract");
const extractLoader  = document.getElementById("extract-loader");
const extractText    = btnExtract.querySelector(".btn-text");

const dataGrid       = document.getElementById("data-grid");
const summaryGrid    = document.getElementById("summary-grid");
const btnBackUpload  = document.getElementById("btn-back-upload");
const btnGenerate    = document.getElementById("btn-generate");
const generateLoader = document.getElementById("generate-loader");
const generateText   = btnGenerate.querySelector(".btn-text");

const btnDownload    = document.getElementById("btn-download");
const btnNewBill     = document.getElementById("btn-new-bill");

const toast          = document.getElementById("toast");
const toastMsg       = document.getElementById("toast-message");
const toastClose     = document.getElementById("toast-close");
const statusMsg      = document.getElementById("statusMessage");

// ── Field config ───────────────────────────────────────────────
const FIELD_LABELS = {
    consumer_name:     "Consumer Name",
    consumer_number:   "Consumer Number",
    billing_period:    "Billing Period",
    units_consumed:    "Units Consumed (kWh)",
    sanctioned_load:   "Sanctioned Load (kW)",
    tariff_category:   "Tariff Category",
    total_bill_amount: "Total Bill Amount (₹)",
    electricity_rate:  "Electricity Rate (₹/kWh)",
    energy_charges:    "Energy Charges (₹)",
    fixed_charges:     "Fixed / Meter Charges (₹)",
    taxes_and_duties:  "Taxes & Duties (₹)",
    meter_number:      "Meter Number",
    supply_type:       "Supply Type",
    due_date:          "Due Date",
    additional_info:   "Additional Info",
};

const PRIORITY_FIELDS = [
    "consumer_name", "consumer_number", "billing_period",
    "units_consumed", "sanctioned_load", "tariff_category",
    "total_bill_amount", "electricity_rate",
    "energy_charges", "fixed_charges", "taxes_and_duties",
];

const NUMERIC_FIELDS = [
    "units_consumed", "sanctioned_load", "total_bill_amount",
    "electricity_rate", "previous_reading", "current_reading",
    "energy_charges", "fixed_charges", "taxes_and_duties",
];


// ════════════════════════════════════════════════════════════════
// STEP CONTROL
// ════════════════════════════════════════════════════════════════

const SECTIONS = [
    document.getElementById("step-upload"),
    document.getElementById("step-review"),
    document.getElementById("step-generate"),
];

const SIDEBAR_NAV = [
    document.getElementById("nav-1"),
    document.getElementById("nav-2"),
    document.getElementById("nav-3"),
];

const PAGE_TITLES = [
    ["Upload Bill",      "AI-powered extraction for MSEDCL, Adani & Tata Power"],
    ["Bill Analysis",    "Review extracted data and ROI projection"],
    ["Download Report",  "Your solar proposal is ready to download"],
];

function showStep(n) {
    SECTIONS.forEach((el, i) => el.classList.toggle("active", i + 1 === n));

    SIDEBAR_NAV.forEach((el, i) => {
        el.classList.remove("active", "completed");
        el.removeAttribute("aria-current");
        if (i + 1 === n)    { el.classList.add("active");    el.setAttribute("aria-current", "page"); }
        else if (i + 1 < n)   el.classList.add("completed");
    });

    const [title, subtitle] = PAGE_TITLES[n - 1] || ["", ""];
    document.getElementById("page-title").textContent    = title;
    document.getElementById("page-subtitle").textContent = subtitle;

    announce(title);

    const wizard = document.getElementById("wizard");
    if (wizard) wizard.scrollTop = 0;
}


// ════════════════════════════════════════════════════════════════
// ACCESSIBILITY
// ════════════════════════════════════════════════════════════════

function announce(msg) {
    statusMsg.textContent = "";
    requestAnimationFrame(() => { statusMsg.textContent = msg; });
    setTimeout(() => { statusMsg.textContent = ""; }, 3000);
}

function showToast(message, duration = 6000) {
    toastMsg.textContent = message;
    toast.classList.remove("hidden");
    requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add("show")));
    if (duration > 0) setTimeout(hideToast, duration);
}

function hideToast() {
    toast.classList.remove("show");
    setTimeout(() => toast.classList.add("hidden"), 360);
}

toastClose.addEventListener("click", hideToast);


// ════════════════════════════════════════════════════════════════
// FILE HANDLING
// ════════════════════════════════════════════════════════════════

function formatBytes(bytes) {
    if (bytes < 1024)        return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function setFile(file) {
    if (!file) return;
    const ext = file.name.split(".").pop().toLowerCase();
    const allowed = ["pdf", "png", "jpg", "jpeg", "webp", "bmp", "tiff"];
    if (!allowed.includes(ext)) {
        showToast(`Unsupported format .${ext} — please use PDF, PNG, or JPG.`);
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        showToast("File too large — maximum is 10 MB.");
        return;
    }
    selectedFile = file;
    fileNameEl.textContent         = file.name;
    fileSizeEl.textContent         = formatBytes(file.size);
    filePreview.classList.remove("hidden");
    uploadZone.style.opacity       = "0.5";
    uploadZone.style.pointerEvents = "none";
    btnExtract.disabled = false;
}

function clearFile() {
    selectedFile = null;
    fileInput.value = "";
    filePreview.classList.add("hidden");
    uploadZone.style.opacity       = "";
    uploadZone.style.pointerEvents = "";
    btnExtract.disabled = true;
}

uploadZone.addEventListener("click",   () => fileInput.click());
uploadZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
});
fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
btnRemove.addEventListener("click",  clearFile);

uploadZone.addEventListener("dragover",  (e) => { e.preventDefault(); uploadZone.classList.add("dragover"); });
uploadZone.addEventListener("dragleave", ()  => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    setFile(e.dataTransfer.files[0]);
});


// ════════════════════════════════════════════════════════════════
// SIZING MATH  (mirrors pdf_generator.py)
// ════════════════════════════════════════════════════════════════

// Solar sizing constants — match pdf_generator.py exactly
const PEAK_SUN_HOURS    = 4.5;   // h/day, India average
const PERF_RATIO        = 0.75;  // system efficiency (inverter + cable + dust + temp)
const GROWTH_BUFFER     = 1.20;  // 20% for degradation, cloudy days, future growth
const MONTHLY_YIELD_PER_KW = PEAK_SUN_HOURS * 30 * PERF_RATIO;  // 101.25 kWh/kW/month

function computeSizing(data) {
    const units   = parseFloat(data.units_consumed)    || 0;
    const rate    = parseFloat(data.electricity_rate)  || 0;
    const bill    = parseFloat(data.total_bill_amount) || 0;
    const monthly = bill > 0 ? bill : (units * rate || 0);

    // Industry-standard formula:
    //   base_kw = units / monthly_yield_per_kw
    //   +20% buffer → round up to next whole kW
    const kw      = units > 0 ? Math.ceil((units / MONTHLY_YIELD_PER_KW) * GROWTH_BUFFER) : 0;
    const panels  = Math.ceil((kw * 1000) / 400) || 0;
    const area    = kw * 100;
    const cost    = kw * 55000;
    const annSav  = monthly * 12 * 0.90;
    const payback = annSav > 0 ? cost / annSav : 0;

    let savings25 = 0;
    for (let k = 0; k < 25; k++) savings25 += annSav * Math.pow(1.03, k);
    savings25 -= cost;

    return { kw, panels, area, cost, annSav, payback, savings25 };
}

function fmtINR(v) {
    if (!v || isNaN(v)) return "—";
    if (v >= 1_00_00_000) return `₹${(v / 1_00_00_000).toFixed(1)}Cr`;
    if (v >= 1_00_000)    return `₹${(v / 1_00_000).toFixed(1)}L`;
    if (v >= 1_000)       return `₹${Math.round(v / 1000)}K`;
    return `₹${Math.round(v)}`;
}


// ════════════════════════════════════════════════════════════════
// KPI CARDS + SIZING LIST  (step 2)
// ════════════════════════════════════════════════════════════════

function updateKPICards(data) {
    const units = parseFloat(data.units_consumed)    || 0;
    const rate  = parseFloat(data.electricity_rate)  || 0;
    const bill  = parseFloat(data.total_bill_amount) || 0;
    const load  = parseFloat(data.sanctioned_load)   || 0;

    const sz = computeSizing(data);

    setText("kpi-units",  units  ? units.toFixed(0)  : "—");
    setText("kpi-rate",   rate   ? rate.toFixed(2)   : "—");
    setText("kpi-load",   load   ? load.toFixed(1)   : "—");
    setText("kpi-amount", bill   ? `₹${Math.round(bill).toLocaleString("en-IN")}` : "—");
    setText("kpi-period", data.billing_period || "—");
    setText("kpi-kw",     sz.kw  ? `${sz.kw}` : "—");
}

function updateSizingList(data) {
    const sz = computeSizing(data);
    setText("sz-val-kw",      sz.kw      ? `${sz.kw} kW`      : "—");
    setText("sz-val-panels",  sz.panels  ? `${sz.panels}`     : "—");
    setText("sz-val-area",    sz.area    ? `${sz.area} sq.ft` : "—");
    setText("sz-val-cost",    fmtINR(sz.cost));
    setText("sz-val-savings", fmtINR(sz.annSav));
    setText("sz-val-payback", sz.payback ? `${sz.payback.toFixed(1)} yrs` : "—");
}

function updateSummaryKPIs(data) {
    const sz = computeSizing(data);
    setText("sum-kw",       sz.kw      ? `${sz.kw}`          : "—");
    setText("sum-panels",   sz.panels  ? `${sz.panels}`      : "—");
    setText("sum-area",     sz.area    ? `${sz.area}`        : "—");
    setText("sum-cost",     fmtINR(sz.cost));
    setText("sum-savings1", fmtINR(sz.annSav));
    setText("sum-payback",  sz.payback ? `${sz.payback.toFixed(1)}` : "—");

    setText("sum-sz-kw",      sz.kw      ? `${sz.kw} kW`      : "—");
    setText("sum-sz-panels",  sz.panels  ? `${sz.panels} panels` : "—");
    setText("sum-sz-area",    sz.area    ? `${sz.area} sq.ft` : "—");
    setText("sum-savings25",  fmtINR(sz.savings25 > 0 ? sz.savings25 : 0));
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}


// ════════════════════════════════════════════════════════════════
// STEP 1 → 2 : EXTRACT
// ════════════════════════════════════════════════════════════════

btnExtract.addEventListener("click", async () => {
    if (!selectedFile) return;

    extractText.classList.add("hidden");
    extractLoader.classList.remove("hidden");
    btnExtract.disabled = true;

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
        const res  = await fetch("/api/extract", { method: "POST", body: formData });
        const json = await parseJsonOrThrow(res);
        if (!res.ok) throw new Error(json.error || "Extraction failed.");

        extractedData = json.data;
        buildDataGrid(dataGrid, extractedData, false);
        updateKPICards(extractedData);
        updateSizingList(extractedData);
        renderChart(extractedData);
        showStep(2);

    } catch (err) {
        showToast(`❌ ${err.message}`);
        announce(`Error: ${err.message}`);
    } finally {
        extractText.classList.remove("hidden");
        extractLoader.classList.add("hidden");
        btnExtract.disabled = !selectedFile;
    }
});

btnBackUpload.addEventListener("click", () => showStep(1));


// ════════════════════════════════════════════════════════════════
// DATA GRID BUILDER
// ════════════════════════════════════════════════════════════════

function buildDataGrid(container, data, readonly) {
    container.innerHTML = "";

    const otherFields = Object.keys(data).filter(
        (k) => !PRIORITY_FIELDS.includes(k) && data[k] !== null && data[k] !== undefined
    );
    const allFields = [...PRIORITY_FIELDS, ...otherFields];

    allFields.forEach((key) => {
        const value = data[key];
        if (value === null || value === undefined) return;
        appendRow(container, key, String(value ?? ""), readonly);
    });

    if (!readonly) {
        PRIORITY_FIELDS.forEach((key) => {
            if (data[key] !== null && data[key] !== undefined) return;
            appendRow(container, key, "", false, "Not found — enter manually");
        });
    }
}

function appendRow(container, key, value, readonly, placeholder = "") {
    const label   = FIELD_LABELS[key] || key.replace(/_/g, " ");
    const fieldId = `field-${readonly ? "ro" : "ed"}-${key}`;

    const row = document.createElement("div");
    row.className = "data-row";
    row.innerHTML = `
        <label class="data-label" for="${fieldId}">${escapeHtml(label)}</label>
        <input class="data-input"
               id="${fieldId}"
               type="text"
               value="${escapeHtml(value)}"
               data-field="${escapeHtml(key)}"
               ${readonly    ? "readonly"                                   : ""}
               ${placeholder ? `placeholder="${escapeHtml(placeholder)}"` : ""}
               aria-label="${escapeHtml(label)}">
    `;
    container.appendChild(row);
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/"/g, "&quot;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

function collectGridValues() {
    const result = {};
    dataGrid.querySelectorAll(".data-input").forEach((input) => {
        const field = input.dataset.field;
        const raw   = input.value.trim();
        if (NUMERIC_FIELDS.includes(field) && raw !== "") {
            const num = parseFloat(raw.replace(/[,₹Rs\s]/g, ""));
            result[field] = isNaN(num) ? null : num;
        } else {
            result[field] = raw || null;
        }
    });
    return result;
}

// Live updates as user edits fields
dataGrid.addEventListener("input", () => {
    const vals = collectGridValues();
    renderChart(vals);
    updateKPICards(vals);
    updateSizingList(vals);
});


// ════════════════════════════════════════════════════════════════
// ROI CHART
// ════════════════════════════════════════════════════════════════

function cumulativeCost(monthlyBill, years) {
    let total = 0;
    for (let k = 0; k < years; k++) total += monthlyBill * 12 * Math.pow(1.03, k);
    return Math.round(total);
}

function renderChart(data) {
    const bill    = parseFloat(data.total_bill_amount) || 0;
    const units   = parseFloat(data.units_consumed)    || 0;
    const rate    = parseFloat(data.electricity_rate)  || 0;
    const monthly = bill > 0 ? bill : (units > 0 && rate > 0 ? units * rate : 0);

    const horizons     = [5, 10, 20];
    const withoutSolar = horizons.map((y) => cumulativeCost(monthly, y));
    const withSolar    = horizons.map((y) => Math.round(cumulativeCost(monthly, y) * 0.10));

    const canvas = document.getElementById("roiChart");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    if (roiChart) {
        roiChart.data.datasets[0].data = withoutSolar;
        roiChart.data.datasets[1].data = withSolar;
        roiChart.update("active");
        return;
    }

    roiChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["5 Years", "10 Years", "20 Years"],
            datasets: [
                {
                    label: "Without Solar",
                    data: withoutSolar,
                    backgroundColor: "rgba(234, 179, 8, 0.80)",
                    borderColor:     "rgba(234, 179, 8, 1)",
                    borderWidth: 1.5,
                    borderRadius: 6,
                    borderSkipped: false,
                },
                {
                    label: "With Solar",
                    data: withSolar,
                    backgroundColor: "rgba(34, 197, 94, 0.80)",
                    borderColor:     "rgba(34, 197, 94, 1)",
                    borderWidth: 1.5,
                    borderRadius: 6,
                    borderSkipped: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: {
                    labels: {
                        font: { family: "'Inter', sans-serif", size: 11, weight: "600" },
                        color: "#6b7280",
                        usePointStyle: true,
                        pointStyleWidth: 9,
                        padding: 16,
                    },
                },
                tooltip: {
                    backgroundColor: "#111827",
                    titleFont: { family: "'Inter', sans-serif", size: 12, weight: "700" },
                    bodyFont:  { family: "'Inter', sans-serif", size: 11 },
                    padding: 12,
                    cornerRadius: 9,
                    callbacks: {
                        label(ctx) {
                            return `  ${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString("en-IN", {
                                style: "currency", currency: "INR", maximumFractionDigits: 0,
                            })}`;
                        },
                        afterBody(items) {
                            if (items.length < 2) return [];
                            const saved = items[0].parsed.y - items[1].parsed.y;
                            return [
                                "",
                                `  Savings: ${saved.toLocaleString("en-IN", {
                                    style: "currency", currency: "INR", maximumFractionDigits: 0,
                                })}`,
                            ];
                        },
                    },
                },
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        font: { family: "'Inter', sans-serif", size: 11, weight: "600" },
                        color: "#6b7280",
                    },
                },
                y: {
                    grid: { color: "rgba(229,231,235,.8)" },
                    ticks: {
                        font:  { family: "'Inter', sans-serif", size: 10 },
                        color: "#9ca3af",
                        callback(v) {
                            if (v >= 1_00_00_000) return `₹${(v / 1_00_00_000).toFixed(1)}Cr`;
                            if (v >= 1_00_000)    return `₹${(v / 1_00_000).toFixed(0)}L`;
                            if (v >= 1_000)       return `₹${(v / 1_000).toFixed(0)}K`;
                            return `₹${v}`;
                        },
                    },
                },
            },
        },
    });
}


// ════════════════════════════════════════════════════════════════
// STEP 2 → 3 : GENERATE ZIP
// ════════════════════════════════════════════════════════════════

btnGenerate.addEventListener("click", async () => {
    const payload = collectGridValues();

    generateText.classList.add("hidden");
    generateLoader.classList.remove("hidden");
    btnGenerate.disabled = true;

    try {
        const res = await fetch("/api/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const json = await parseJsonOrThrow(res);
            throw new Error(json.error || "Report generation failed.");
        }

        const blob = await res.blob();
        if (downloadUrl) URL.revokeObjectURL(downloadUrl);
        downloadUrl = URL.createObjectURL(blob);

        btnDownload.href     = downloadUrl;
        btnDownload.download = "Energybae_Solar_Proposal.zip";

        buildDataGrid(summaryGrid, payload, true);
        updateSummaryKPIs(payload);

        showStep(3);
        announce("Proposal ready. Click Download to save your ZIP.");

    } catch (err) {
        showToast(`❌ ${err.message}`);
        announce(`Error: ${err.message}`);
    } finally {
        generateText.classList.remove("hidden");
        generateLoader.classList.add("hidden");
        btnGenerate.disabled = false;
    }
});


// ════════════════════════════════════════════════════════════════
// RESET
// ════════════════════════════════════════════════════════════════

btnNewBill.addEventListener("click", () => {
    if (downloadUrl) { URL.revokeObjectURL(downloadUrl); downloadUrl = ""; }
    if (roiChart)    { roiChart.destroy(); roiChart = null; }

    clearFile();
    extractedData        = {};
    dataGrid.innerHTML   = "";
    summaryGrid.innerHTML = "";

    showStep(1);
});


// ════════════════════════════════════════════════════════════════
// SAFE JSON PARSER
// ════════════════════════════════════════════════════════════════

async function parseJsonOrThrow(res) {
    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("application/json")) {
        // Render free-tier returns <!DOCTYPE html> while the service wakes up
        const status = res.status;
        if (status === 502 || status === 503 || status === 0) {
            throw new Error(
                "Server is starting up (cold start). Please wait 20–30 seconds and try again."
            );
        }
        throw new Error(
            `Unexpected server response (HTTP ${status}). The server may be restarting — please try again.`
        );
    }
    return res.json();
}


// ════════════════════════════════════════════════════════════════
// KEEP-ALIVE  (prevents Render free-tier from sleeping)
// ════════════════════════════════════════════════════════════════

async function pingServer() {
    try { await fetch("/api/health"); } catch (_) {}
}
pingServer();                            // warm-up on page load
setInterval(pingServer, 4 * 60 * 1000); // ping every 4 min to stay awake


// ════════════════════════════════════════════════════════════════
// INIT
// ════════════════════════════════════════════════════════════════

showStep(1);
