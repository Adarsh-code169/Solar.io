/**
 * Solar Load Calculator — Frontend Logic
 * Handles: file upload, drag-and-drop, API calls, data preview, Excel download
 */

// ── State ──────────────────────────────────────────────────────────────
let selectedFile = null;
let extractedData = {};
let downloadUrl = "";

// ── DOM References ─────────────────────────────────────────────────────
const uploadZone    = document.getElementById("upload-zone");
const fileInput     = document.getElementById("file-input");
const filePreview   = document.getElementById("file-preview");
const fileName      = document.getElementById("file-name");
const fileSize      = document.getElementById("file-size");
const btnRemove     = document.getElementById("btn-remove");
const btnExtract    = document.getElementById("btn-extract");
const extractLoader = document.getElementById("extract-loader");
const extractText   = btnExtract.querySelector(".btn-text");

const step1         = document.getElementById("step-1");
const step2         = document.getElementById("step-2");
const step3         = document.getElementById("step-3");
const dataGrid      = document.getElementById("data-grid");

const btnBackToOne  = document.getElementById("btn-back-1");
const btnGenerate   = document.getElementById("btn-generate");
const generateLoader = document.getElementById("generate-loader");
const generateText  = btnGenerate.querySelector(".btn-text");

const outputFilename = document.getElementById("output-filename");
const btnDownload   = document.getElementById("btn-download");
const btnNew        = document.getElementById("btn-new");

const toast         = document.getElementById("toast");
const toastMsg      = document.getElementById("toast-message");
const toastClose    = document.getElementById("toast-close");

// ── Field display names ────────────────────────────────────────────────
const FIELD_LABELS = {
  consumer_name:    "Consumer Name",
  consumer_number:  "Consumer Number",
  billing_period:   "Billing Period",
  units_consumed:   "Units Consumed (kWh)",
  sanctioned_load:  "Sanctioned Load (kW)",
  tariff_category:  "Tariff Category",
  total_bill_amount: "Total Bill Amount (₹)",
  electricity_rate: "Electricity Rate (₹/kWh)",
  meter_number:     "Meter Number",
  supply_type:      "Supply Type",
  due_date:         "Due Date",
  additional_info:  "Additional Info",
};

// Fields shown at the top in the review grid (priority fields)
const PRIORITY_FIELDS = [
  "consumer_name", "consumer_number", "billing_period",
  "units_consumed", "sanctioned_load", "tariff_category",
  "total_bill_amount", "electricity_rate",
];

// ── Step Navigation ────────────────────────────────────────────────────
function showStep(num) {
  [step1, step2, step3].forEach((s, i) => {
    s.classList.toggle("hidden", i + 1 !== num);
  });

  document.querySelectorAll(".step").forEach((el, i) => {
    el.classList.remove("active", "completed");
    if (i < num - 1) el.classList.add("completed");
    if (i === num - 1) el.classList.add("active");
  });

  document.querySelectorAll(".step-line").forEach((line, i) => {
    line.classList.toggle("active", i < num - 1);
  });
}

// ── Toast Notifications ────────────────────────────────────────────────
function showToast(message, duration = 5000) {
  toastMsg.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("show"), 10);
  if (duration > 0) setTimeout(hideToast, duration);
}

function hideToast() {
  toast.classList.remove("show");
  setTimeout(() => toast.classList.add("hidden"), 400);
}

toastClose.addEventListener("click", hideToast);

// ── File Handling ──────────────────────────────────────────────────────
function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function setFile(file) {
  if (!file) return;

  const ext = file.name.split(".").pop().toLowerCase();
  const allowed = ["pdf","png","jpg","jpeg","webp","bmp","tiff"];
  if (!allowed.includes(ext)) {
    showToast(`Unsupported format: .${ext}. Use PDF, PNG, or JPG.`);
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showToast("File too large. Maximum size is 10 MB.");
    return;
  }

  selectedFile = file;
  fileName.textContent = file.name;
  fileSize.textContent = formatBytes(file.size);
  filePreview.classList.remove("hidden");
  uploadZone.style.opacity = "0.5";
  uploadZone.style.pointerEvents = "none";
  btnExtract.disabled = false;
}

function clearFile() {
  selectedFile = null;
  fileInput.value = "";
  filePreview.classList.add("hidden");
  uploadZone.style.opacity = "";
  uploadZone.style.pointerEvents = "";
  btnExtract.disabled = true;
}

// Upload zone click
uploadZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
btnRemove.addEventListener("click", clearFile);

// Drag-and-drop
uploadZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadZone.classList.add("dragover");
});
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadZone.classList.remove("dragover");
  setFile(e.dataTransfer.files[0]);
});

// ── Extract (Step 1 → 2) ───────────────────────────────────────────────
btnExtract.addEventListener("click", async () => {
  if (!selectedFile) return;

  // Show loader
  extractText.classList.add("hidden");
  extractLoader.classList.remove("hidden");
  btnExtract.disabled = true;

  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    const res = await fetch("/api/extract", { method: "POST", body: formData });
    const json = await res.json();

    if (!res.ok) throw new Error(json.error || "Extraction failed");

    extractedData = json.data;
    buildDataGrid(extractedData);
    showStep(2);

  } catch (err) {
    showToast(`❌ ${err.message}`);
  } finally {
    extractText.classList.remove("hidden");
    extractLoader.classList.add("hidden");
    btnExtract.disabled = false;
  }
});

// ── Build Data Review Grid ─────────────────────────────────────────────
function buildDataGrid(data) {
  dataGrid.innerHTML = "";

  // Show priority fields first, then remaining non-null fields
  const otherFields = Object.keys(data).filter(
    k => !PRIORITY_FIELDS.includes(k) && data[k] !== null && data[k] !== undefined
  );
  const allFields = [...PRIORITY_FIELDS, ...otherFields];

  allFields.forEach(key => {
    const label = FIELD_LABELS[key] || key.replace(/_/g, " ");
    const value = data[key];
    if (value === null || value === undefined) return;

    const row = document.createElement("div");
    row.className = "data-row";
    row.innerHTML = `
      <label class="data-label" for="field-${key}">${label}</label>
      <input class="data-input" id="field-${key}" type="text"
             value="${escapeHtml(String(value ?? ""))}"
             data-field="${key}">
    `;
    dataGrid.appendChild(row);
  });

  // Add null priority fields as empty editable rows
  PRIORITY_FIELDS.forEach(key => {
    if (data[key] !== null && data[key] !== undefined) return;
    const label = FIELD_LABELS[key] || key.replace(/_/g, " ");
    const row = document.createElement("div");
    row.className = "data-row";
    row.innerHTML = `
      <label class="data-label" for="field-${key}">${label}</label>
      <input class="data-input" id="field-${key}" type="text"
             placeholder="Not found — enter manually"
             data-field="${key}">
    `;
    dataGrid.appendChild(row);
  });
}

function escapeHtml(str) {
  return str.replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// ── Back to Step 1 ─────────────────────────────────────────────────────
btnBackToOne.addEventListener("click", () => showStep(1));

// ── Generate Excel (Step 2 → 3) ────────────────────────────────────────
btnGenerate.addEventListener("click", async () => {
  // Collect edited values from the grid inputs
  const inputs = dataGrid.querySelectorAll(".data-input");
  const payload = {};

  inputs.forEach(input => {
    const field = input.dataset.field;
    let val = input.value.trim();

    // Attempt numeric coercion for known numeric fields
    const numericFields = [
      "units_consumed", "sanctioned_load", "total_bill_amount",
      "electricity_rate", "previous_reading", "current_reading",
    ];
    if (numericFields.includes(field) && val !== "") {
      const num = parseFloat(val.replace(/[,₹Rs\s]/g, ""));
      payload[field] = isNaN(num) ? null : num;
    } else {
      payload[field] = val || null;
    }
  });

  // Show loader
  generateText.classList.add("hidden");
  generateLoader.classList.remove("hidden");
  btnGenerate.disabled = true;

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const json = await res.json();

    if (!res.ok) throw new Error(json.error || "Generation failed");

    downloadUrl = json.download_url;
    outputFilename.textContent = json.filename;
    btnDownload.href = downloadUrl;
    btnDownload.download = json.filename;
    showStep(3);

  } catch (err) {
    showToast(`❌ ${err.message}`);
  } finally {
    generateText.classList.remove("hidden");
    generateLoader.classList.add("hidden");
    btnGenerate.disabled = false;
  }
});

// ── Process Another Bill ───────────────────────────────────────────────
btnNew.addEventListener("click", () => {
  clearFile();
  extractedData = {};
  downloadUrl = "";
  dataGrid.innerHTML = "";
  showStep(1);
});

// ── Init ───────────────────────────────────────────────────────────────
showStep(1);
