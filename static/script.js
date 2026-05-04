/**
 * SolarCloud — Frontend Logic
 *
 * State machine: step-upload → step-review → step-generate
 * Handles: file upload, drag-drop, AI extraction, live ROI chart,
 *          ZIP proposal download, accessibility announcements.
 */

"use strict";

// ── State ──────────────────────────────────────────────────────────────
let selectedFile  = null;
let extractedData = {};
let downloadUrl   = "";
let roiChart      = null;      // Chart.js instance (destroyed on reset)

// ── DOM refs ───────────────────────────────────────────────────────────
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

// ── Field config ───────────────────────────────────────────────────────
const FIELD_LABELS = {
    consumer_name:     "Consumer Name",
    consumer_number:   "Consumer Number",
    billing_period:    "Billing Period",
    units_consumed:    "Units Consumed (kWh)",
    sanctioned_load:   "Sanctioned Load (kW)",
    tariff_category:   "Tariff Category",
    total_bill_amount: "Total Bill Amount (₹)",
    electricity_rate:  "Electricity Rate (₹/kWh)",
    meter_number:      "Meter Number",
    supply_type:       "Supply Type",
    due_date:          "Due Date",
    additional_info:   "Additional Info",
};

const PRIORITY_FIELDS = [
    "consumer_name", "consumer_number", "billing_period",
    "units_consumed", "sanctioned_load", "tariff_category",
    "total_bill_amount", "electricity_rate",
];

const NUMERIC_FIELDS = [
    "units_consumed", "sanctioned_load", "total_bill_amount",
    "electricity_rate", "previous_reading", "current_reading",
];


// ════════════════════════════════════════════════════════════════
// STEP CONTROL
// ════════════════════════════════════════════════════════════════

const SECTIONS = [
    document.getElementById("step-upload"),
    document.getElementById("step-review"),
    document.getElementById("step-generate"),
];
const NAV_ITEMS = [
    document.getElementById("nav-1"),
    document.getElementById("nav-2"),
    document.getElementById("nav-3"),
];
const CONNECTORS = [
    document.getElementById("conn-1"),
    document.getElementById("conn-2"),
];
const STEP_LABELS = ["Upload your bill", "Review extracted data", "Download your proposal"];

function showStep(n) {
    // Toggle sections (1-indexed)
    SECTIONS.forEach((el, i) => el.classList.toggle("active", i + 1 === n));

    // Update nav indicators
    NAV_ITEMS.forEach((el, i) => {
        el.classList.remove("active", "completed");
        if (i + 1 === n)    el.classList.add("active");
        else if (i + 1 < n) el.classList.add("completed");
    });

    // Update connectors
    CONNECTORS.forEach((el, i) => {
        el.classList.remove("active", "completed");
        if (i + 1 < n - 1) el.classList.add("completed");
        if (i + 1 === n - 1) el.classList.add("active");
    });

    announce(STEP_LABELS[n - 1] || "");

    // Scroll the wizard back to top (mobile)
    const wizard = document.getElementById("wizard");
    if (wizard) wizard.scrollTop = 0;
}


// ════════════════════════════════════════════════════════════════
// ACCESSIBILITY  — live region + toast
// ════════════════════════════════════════════════════════════════

function announce(msg) {
    statusMsg.textContent = "";                      // reset first so repeat text re-fires
    requestAnimationFrame(() => { statusMsg.textContent = msg; });
    setTimeout(() => { statusMsg.textContent = ""; }, 3000);
}

function showToast(message, duration = 6000) {
    toastMsg.textContent = message;
    toast.classList.remove("hidden");
    requestAnimationFrame(() => {
        requestAnimationFrame(() => toast.classList.add("show"));
    });
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
    if (bytes < 1024)           return `${bytes} B`;
    if (bytes < 1024 * 1024)    return `${(bytes / 1024).toFixed(1)} KB`;
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
    fileNameEl.textContent  = file.name;
    fileSizeEl.textContent  = formatBytes(file.size);
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

// Click / keyboard on upload zone
uploadZone.addEventListener("click", () => fileInput.click());
uploadZone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
});
fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
btnRemove.addEventListener("click",  clearFile);

// Drag-and-drop
uploadZone.addEventListener("dragover",  (e) => { e.preventDefault(); uploadZone.classList.add("dragover"); });
uploadZone.addEventListener("dragleave", ()  => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    setFile(e.dataTransfer.files[0]);
});


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
        const json = await res.json();
        if (!res.ok) throw new Error(json.error || "Extraction failed.");

        extractedData = json.data;
        buildDataGrid(dataGrid, extractedData, false);
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

// Back to upload
btnBackUpload.addEventListener("click", () => showStep(1));


// ════════════════════════════════════════════════════════════════
// DATA GRID BUILDER  (shared by review + summary)
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

    // Empty priority fields: only add editable placeholders in review mode
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
               ${readonly        ? "readonly"                          : ""}
               ${placeholder     ? `placeholder="${escapeHtml(placeholder)}"` : ""}
               aria-label="${escapeHtml(label)}">
    `;
    container.appendChild(row);
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g,  "&amp;")
        .replace(/"/g,  "&quot;")
        .replace(/</g,  "&lt;")
        .replace(/>/g,  "&gt;");
}

// Collect current form values (for live chart + generate payload)
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

// Live chart update when user edits any field
dataGrid.addEventListener("input", () => renderChart(collectGridValues()));


// ════════════════════════════════════════════════════════════════
// ROI CHART
// ════════════════════════════════════════════════════════════════

function cumulativeCost(monthlyBill, years) {
    let total = 0;
    for (let k = 0; k < years; k++) total += monthlyBill * 12 * Math.pow(1.03, k);
    return Math.round(total);
}

function renderChart(data) {
    const bill   = parseFloat(data.total_bill_amount) || 0;
    const units  = parseFloat(data.units_consumed)    || 0;
    const rate   = parseFloat(data.electricity_rate)  || 0;
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
                    backgroundColor: "rgba(37, 99, 235, 0.75)",
                    borderColor:     "rgba(37, 99, 235, 1)",
                    borderWidth: 1.5,
                    borderRadius: 7,
                    borderSkipped: false,
                },
                {
                    label: "With Solar",
                    data: withSolar,
                    backgroundColor: "rgba(16, 185, 129, 0.75)",
                    borderColor:     "rgba(16, 185, 129, 1)",
                    borderWidth: 1.5,
                    borderRadius: 7,
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
                        font: { family: "'Inter', sans-serif", size: 12, weight: "600" },
                        color: "#475569",
                        usePointStyle: true,
                        pointStyleWidth: 10,
                        padding: 20,
                    },
                },
                tooltip: {
                    backgroundColor: "#0f172a",
                    titleFont: { family: "'Inter', sans-serif", size: 13, weight: "700" },
                    bodyFont:  { family: "'Inter', sans-serif", size: 12 },
                    padding: 14,
                    cornerRadius: 10,
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
                                `  💰 Savings: ${saved.toLocaleString("en-IN", {
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
                        font: { family: "'Inter', sans-serif", size: 12, weight: "600" },
                        color: "#475569",
                    },
                },
                y: {
                    grid: { color: "rgba(226, 232, 240, 0.8)" },
                    ticks: {
                        font:  { family: "'Inter', sans-serif", size: 11 },
                        color: "#94a3b8",
                        callback(v) {
                            if (v >= 1_00_00_000) return `₹${(v / 1_00_00_000).toFixed(1)}Cr`;
                            if (v >= 1_00_000)   return `₹${(v / 1_00_000).toFixed(0)}L`;
                            if (v >= 1_000)      return `₹${(v / 1_000).toFixed(0)}K`;
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

        // Errors return JSON with a non-2xx status
        if (!res.ok) {
            const json = await res.json();
            throw new Error(json.error || "Report generation failed.");
        }

        // Success: backend returns the ZIP blob directly
        const blob = await res.blob();
        if (downloadUrl) URL.revokeObjectURL(downloadUrl);
        downloadUrl = URL.createObjectURL(blob);

        btnDownload.href     = downloadUrl;
        btnDownload.download = "Energybae_Solar_Proposal.zip";

        // Populate read-only summary panel (left side of step 3)
        buildDataGrid(summaryGrid, payload, true);

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
// RESET — process another bill
// ════════════════════════════════════════════════════════════════

btnNewBill.addEventListener("click", () => {
    // Release object URL to avoid memory leak
    if (downloadUrl) { URL.revokeObjectURL(downloadUrl); downloadUrl = ""; }

    // Destroy chart so it can be rebuilt fresh on next extraction
    if (roiChart) { roiChart.destroy(); roiChart = null; }

    clearFile();
    extractedData = {};
    dataGrid.innerHTML    = "";
    summaryGrid.innerHTML = "";

    showStep(1);
});


// ════════════════════════════════════════════════════════════════
// INIT
// ════════════════════════════════════════════════════════════════

showStep(1);
