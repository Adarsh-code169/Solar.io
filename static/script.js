/**
 * Solar Load Calculator — Frontend Logic
 * Handles: file upload, drag-and-drop, API calls, data preview,
 *          live ROI chart, ZIP proposal download
 */

// ── State ──────────────────────────────────────────────────────────────
let selectedFile  = null;
let extractedData = {};
let downloadUrl   = "";
let roiChart      = null;   // Chart.js instance

// ── DOM References ─────────────────────────────────────────────────────
const uploadZone   = document.getElementById("upload-zone");
const fileInput    = document.getElementById("file-input");
const filePreview  = document.getElementById("file-preview");
const fileName     = document.getElementById("file-name");
const fileSize     = document.getElementById("file-size");
const btnRemove    = document.getElementById("btn-remove");
const btnExtract   = document.getElementById("btn-extract");
const extractLoader = document.getElementById("extract-loader");
const extractText  = btnExtract.querySelector(".btn-text");

const step1 = document.getElementById("step-1");
const step2 = document.getElementById("step-2");
const step3 = document.getElementById("step-3");
const dataGrid = document.getElementById("data-grid");

const btnBackToOne  = document.getElementById("btn-back-1");
const btnGenerate   = document.getElementById("btn-generate");
const generateLoader = document.getElementById("generate-loader");
const generateText  = btnGenerate.querySelector(".btn-text");

const outputFilename = document.getElementById("output-filename");
const btnDownload    = document.getElementById("btn-download");
const btnNew         = document.getElementById("btn-new");

const toast     = document.getElementById("toast");
const toastMsg  = document.getElementById("toast-message");
const toastClose = document.getElementById("toast-close");

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

const PRIORITY_FIELDS = [
  "consumer_name", "consumer_number", "billing_period",
  "units_consumed", "sanctioned_load", "tariff_category",
  "total_bill_amount", "electricity_rate",
];

const NUMERIC_FIELDS = [
  "units_consumed", "sanctioned_load", "total_bill_amount",
  "electricity_rate", "previous_reading", "current_reading",
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
  const allowed = ["pdf", "png", "jpg", "jpeg", "webp", "bmp", "tiff"];
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

  // Render chart with initial data
  updateROIChart(data);
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ── Live chart update on input edit ───────────────────────────────────
dataGrid.addEventListener("input", () => {
  const liveData = collectGridValues();
  updateROIChart(liveData);
});

function collectGridValues() {
  const result = {};
  dataGrid.querySelectorAll(".data-input").forEach(input => {
    const field = input.dataset.field;
    let val = input.value.trim();
    if (NUMERIC_FIELDS.includes(field) && val !== "") {
      const num = parseFloat(val.replace(/[,₹Rs\s]/g, ""));
      result[field] = isNaN(num) ? null : num;
    } else {
      result[field] = val || null;
    }
  });
  return result;
}

// ── ROI Chart ──────────────────────────────────────────────────────────
function computeCumulativeCost(monthlyBill, years) {
  let total = 0;
  for (let k = 0; k < years; k++) {
    total += monthlyBill * 12 * Math.pow(1.03, k);
  }
  return Math.round(total);
}

function updateROIChart(data) {
  const bill  = parseFloat(data.total_bill_amount) || 0;
  const units = parseFloat(data.units_consumed)    || 0;
  const rate  = parseFloat(data.electricity_rate)  || 0;

  // Derive monthly baseline: prefer total_bill_amount, fall back to units × rate
  const monthlyBill = bill > 0 ? bill : (units > 0 && rate > 0 ? units * rate : 0);

  const horizons = [5, 10, 20];
  const withoutSolar = horizons.map(y => computeCumulativeCost(monthlyBill, y));
  const withSolar    = horizons.map(y => Math.round(computeCumulativeCost(monthlyBill, y) * 0.10));

  const ctx = document.getElementById("roiChart").getContext("2d");

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
          borderColor: "rgba(37, 99, 235, 1)",
          borderWidth: 1.5,
          borderRadius: 6,
          borderSkipped: false,
        },
        {
          label: "With Solar",
          data: withSolar,
          backgroundColor: "rgba(16, 185, 129, 0.75)",
          borderColor: "rgba(16, 185, 129, 1)",
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
          position: "top",
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
              const val = ctx.parsed.y;
              return `  ${ctx.dataset.label}: ${val.toLocaleString("en-IN", {
                style: "currency", currency: "INR", maximumFractionDigits: 0,
              })}`;
            },
            afterBody(items) {
              if (items.length === 2) {
                const saved = items[0].parsed.y - items[1].parsed.y;
                return [
                  "",
                  `  💰 Savings: ${saved.toLocaleString("en-IN", {
                    style: "currency", currency: "INR", maximumFractionDigits: 0,
                  })}`,
                ];
              }
              return [];
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
            font: { family: "'Inter', sans-serif", size: 11 },
            color: "#94a3b8",
            callback(val) {
              if (val >= 1_00_00_000) return `₹${(val / 1_00_00_000).toFixed(1)}Cr`;
              if (val >= 1_00_000)   return `₹${(val / 1_00_000).toFixed(0)}L`;
              if (val >= 1_000)      return `₹${(val / 1_000).toFixed(0)}K`;
              return `₹${val}`;
            },
          },
        },
      },
    },
  });
}

// ── Back to Step 1 ─────────────────────────────────────────────────────
btnBackToOne.addEventListener("click", () => showStep(1));

// ── Generate ZIP (Step 2 → 3) ──────────────────────────────────────────
btnGenerate.addEventListener("click", async () => {
  const inputs  = dataGrid.querySelectorAll(".data-input");
  const payload = {};

  inputs.forEach(input => {
    const field = input.dataset.field;
    let val = input.value.trim();
    if (NUMERIC_FIELDS.includes(field) && val !== "") {
      const num = parseFloat(val.replace(/[,₹Rs\s]/g, ""));
      payload[field] = isNaN(num) ? null : num;
    } else {
      payload[field] = val || null;
    }
  });

  generateText.classList.add("hidden");
  generateLoader.classList.remove("hidden");
  btnGenerate.disabled = true;

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    // Errors still come back as JSON with a non-2xx status
    if (!res.ok) {
      const json = await res.json();
      throw new Error(json.error || "Generation failed");
    }

    // Success: backend returns a ZIP blob directly
    const blob = await res.blob();
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);   // release previous object URL
    downloadUrl = URL.createObjectURL(blob);

    outputFilename.textContent = "Energybae_Solar_Proposal.zip";
    btnDownload.href = downloadUrl;
    btnDownload.download = "Energybae_Solar_Proposal.zip";
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
  if (downloadUrl) {
    URL.revokeObjectURL(downloadUrl);
    downloadUrl = "";
  }
  if (roiChart) {
    roiChart.destroy();
    roiChart = null;
  }
  clearFile();
  extractedData = {};
  dataGrid.innerHTML = "";
  showStep(1);
});

// ── Init ───────────────────────────────────────────────────────────────
showStep(1);
