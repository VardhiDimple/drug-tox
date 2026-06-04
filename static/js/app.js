/**
 * DRUG TOX PRO — frontend dashboard v2
 */

const panels = document.querySelectorAll(".panel");
const navButtons = document.querySelectorAll(".nav-btn");

function navigateTo(panelId) {
  navButtons.forEach((b) => b.classList.toggle("active", b.dataset.panel === panelId));
  panels.forEach((p) => p.classList.toggle("active", p.id === `panel-${panelId}`));
  window.dispatchEvent(new CustomEvent("panelchange", { detail: { panel: panelId } }));
}

navButtons.forEach((btn) => {
  btn.addEventListener("click", () => navigateTo(btn.dataset.panel));
});

document.querySelectorAll(".feature-card[data-goto]").forEach((card) => {
  card.addEventListener("click", () => navigateTo(card.dataset.goto));
});

function showAlert(containerId, message, type = "error") {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.className = `alert alert-${type}`;
  el.textContent = message;
  el.classList.remove("hidden");
}

function hideAlert(containerId) {
  const el = document.getElementById(containerId);
  if (el) el.classList.add("hidden");
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

function statBox(label, value) {
  return `<div class="stat-box"><div class="value">${value}</div><div class="label">${label}</div></div>`;
}

function riskBadge(label) {
  const map = { Low: "badge-success", Moderate: "badge-warning", High: "badge-danger" };
  return `<span class="badge ${map[label] || "badge-warning"}">${label}</span>`;
}

function renderPreviewTable(records, columns) {
  if (!records?.length) return "<p>No preview data.</p>";
  const cols = columns || Object.keys(records[0]);
  return `<div class="table-scroll"><table class="results-table preview-table"><thead><tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>${records.map((row) => `<tr>${cols.map((c) => `<td>${row[c] ?? ""}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

function renderDatasetInfo(data, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.className = "dataset-info";
  el.innerHTML = `
    <p><strong>Rows:</strong> ${data.shape.rows} &nbsp;·&nbsp; <strong>Columns:</strong> ${data.shape.columns}</p>
    <p><strong>Column names:</strong> ${data.columns.join(", ")}</p>
  `;
  el.classList.remove("hidden");
}

function renderDtypesTable(data, containerId) {
  const el = document.getElementById(containerId);
  if (!el || !data.columns?.length) return;
  const rows = data.columns.map((c) => `<tr><td>${c}</td><td>${data.dtypes?.[c] ?? "—"}</td></tr>`).join("");
  el.innerHTML = `
    <div style="margin-top:0.75rem">
      <p><strong>Data types</strong></p>
      <div class="table-scroll"><table class="results-table"><thead><tr><th>Column</th><th>Type</th></tr></thead><tbody>${rows}</tbody></table></div>
    </div>`;
  el.classList.remove("hidden");
}
function renderMissingSummary(data, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const missing = data.missing_summary || {};
  const keys = Object.keys(missing);
  if (!keys.length) {
    el.innerHTML = `<p class="alert alert-success" style="margin-top:0.75rem">No missing values detected.</p>`;
  } else {
    const rows = keys.map((col) => {
      const stats = data.column_stats?.[col] || {};
      return `<tr><td>${col}</td><td>${missing[col]}</td><td>${stats.missing_pct ?? "—"}%</td></tr>`;
    }).join("");
    el.innerHTML = `
      <div style="margin-top:0.75rem">
        <p><strong>Missing value summary</strong> (${data.total_missing_cells ?? 0} total missing cells)</p>
        <div class="table-scroll"><table class="results-table"><thead><tr><th>Column</th><th>Missing</th><th>%</th></tr></thead><tbody>${rows}</tbody></table></div>
        <p class="text-muted" style="margin-top:0.5rem;font-size:0.8rem">Missing feature values are filled automatically during training. Rows with missing target values are excluded.</p>
      </div>`;
  }
  el.classList.remove("hidden");
}

function renderClassDistribution(dist, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const rows = Object.entries(dist).map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("");
  el.innerHTML = `
    <p><strong>Class distribution</strong></p>
    <table class="results-table"><thead><tr><th>Class</th><th>Count</th></tr></thead><tbody>${rows}</tbody></table>`;
  el.classList.remove("hidden");
}

function getActivePanelId() {
  const active = document.querySelector(".nav-btn.active");
  return active?.dataset?.panel || "home";
}

// Expose app context for chatbot
window.appContext = {
  getPanel: getActivePanelId,
  getMlContext: () => window._mlContext || {},
  getVizContext: () => window._vizContext || {},
  getLastError: () => window._lastError || null,
  setLastError: (err) => { window._lastError = err; },
};

function renderClassificationReport(report, labels) {
  let rows = "";
  for (const label of labels) {
    const r = report[label];
    if (!r || typeof r !== "object") continue;
    rows += `<tr><td>${label}</td><td>${(r.precision ?? 0).toFixed(3)}</td><td>${(r.recall ?? 0).toFixed(3)}</td><td>${(r["f1-score"] ?? 0).toFixed(3)}</td><td>${r.support ?? 0}</td></tr>`;
  }
  return `<table class="results-table"><thead><tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function renderPlotResult(d, chartId = "plotly-chart") {
  let html = `<div class="card"><h3>${d.plot_type} plot</h3>`;
  if (d.plotly_json) html += `<div id="${chartId}" class="plot-container"></div>`;
  if (d.matplotlib_png) html += `<div class="plot-container"><img src="data:image/png;base64,${d.matplotlib_png}" alt="plot"/></div>`;
  html += "</div>";
  return html;
}

function mountPlotly(chartId, plotlyJson) {
  if (plotlyJson && window.Plotly) {
    const fig = JSON.parse(plotlyJson);
    Plotly.newPlot(chartId, fig.data, fig.layout, { responsive: true });
  }
}

// ——— ADMET (unchanged) ———
document.getElementById("admet-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAlert("admet-alert");
  const smiles = document.getElementById("admet-smiles").value.trim();
  if (!smiles) return;

  const results = document.getElementById("admet-results");
  results.innerHTML = '<p class="loading">Computing descriptors with RDKit…</p>';

  const json = await postJSON("/api/admet/predict", { smiles });
  if (!json.success) {
    showAlert("admet-alert", json.error || "Prediction failed");
    window.appContext.setLastError(json.error || "Prediction failed");
    results.innerHTML = "";
    return;
  }

  const d = json.data;
  const tox = d.toxicity.primary;
  const lip = d.lipinski;

  results.innerHTML = `
    <div class="card"><h3>Canonical SMILES</h3><code class="code-block">${d.canonical_smiles}</code></div>
    <div class="card"><h3>Molecular Descriptors (RDKit)</h3>
      <div class="stat-grid">
        ${statBox("MW", d.descriptors.molecular_weight)}${statBox("LogP", d.descriptors.logp)}
        ${statBox("TPSA", d.descriptors.tpsa)}${statBox("HBD", d.descriptors.h_bond_donors)}
        ${statBox("HBA", d.descriptors.h_bond_acceptors)}${statBox("Rot. Bonds", d.descriptors.rotatable_bonds)}
        ${statBox("QED", d.descriptors.qed)}${statBox("Fsp³", d.descriptors.fraction_csp3)}
      </div>
    </div>
    <div class="grid-2">
      <div class="card"><h3>Lipinski Rule of Five</h3><p>${lip.summary}</p>
        <span class="badge ${lip.passed ? "badge-success" : lip.drug_like ? "badge-warning" : "badge-danger"}">${lip.passed ? "PASS" : lip.drug_like ? "DRUG-LIKE" : "FAIL"}</span>
        ${lip.violations.length ? `<table class="results-table" style="margin-top:1rem"><thead><tr><th>Property</th><th>Value</th><th>Limit</th></tr></thead><tbody>${lip.violations.map((v) => `<tr><td>${v.property}</td><td>${v.value}</td><td>${v.operator} ${v.limit}</td></tr>`).join("")}</tbody></table>` : ""}
      </div>
      <div class="card"><h3>Toxicity Prediction</h3>
        <p><strong>${tox.toxicity_class}</strong> ${riskBadge(tox.risk_label)}</p>
        <p>Risk score: <strong>${tox.risk_score}</strong> · Method: <em>${tox.method}</em></p>
        <p class="text-muted">${d.toxicity.note}</p>
      </div>
    </div>
    <div class="card"><h3>ADMET Summary</h3><table class="results-table">
      <tr><th>Absorption</th><td>${d.admet_summary.absorption_hint}</td></tr>
      <tr><th>Distribution</th><td>${d.admet_summary.distribution_hint}</td></tr>
      <tr><th>Metabolism</th><td>${d.admet_summary.metabolism_hint}</td></tr>
      <tr><th>Excretion</th><td>${d.admet_summary.excretion_hint}</td></tr>
      <tr><th>Toxicity</th><td>${d.admet_summary.toxicity_hint}</td></tr>
    </table></div>`;
});

// ——— Molecular Viewer (unchanged) ———
async function loadMoleculeViewer() {
  hideAlert("viewer-alert");
  const smiles = document.getElementById("viewer-smiles").value.trim();
  if (!smiles) return;

  const img2d = document.getElementById("viewer-2d-img");
  const wrap3d = document.getElementById("viewer-3d-wrap");
  img2d.src = `/api/molecule/2d?smiles=${encodeURIComponent(smiles)}&width=420&height=420`;
  img2d.onerror = () => showAlert("viewer-alert", "Could not render 2D structure. Check SMILES.");

  const show3d = document.getElementById("viewer-show-3d").checked;
  wrap3d.classList.toggle("hidden", !show3d);

  if (show3d) {
    try {
      const res = await fetch(`/api/molecule/3d?smiles=${encodeURIComponent(smiles)}`);
      const json = await res.json();
      if (!json.success) { showAlert("viewer-alert", json.error); return; }
      render3DMolecule(json.data);
      document.getElementById("viewer-3d-img").src = `/api/molecule/3d/image?smiles=${encodeURIComponent(smiles)}&t=${Date.now()}`;
      document.getElementById("viewer-3d-img").classList.remove("hidden");
    } catch { showAlert("viewer-alert", "3D generation failed."); }
  }
}

document.getElementById("viewer-form")?.addEventListener("submit", (e) => { e.preventDefault(); loadMoleculeViewer(); });

function render3DMolecule(data) {
  const canvas = document.getElementById("viewer-3d-canvas");
  if (!canvas || !window.THREE) return;
  const width = canvas.clientWidth, height = canvas.clientHeight;
  while (canvas.firstChild) canvas.removeChild(canvas.firstChild);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0f1419);
  const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  canvas.appendChild(renderer.domElement);
  const light = new THREE.DirectionalLight(0xffffff, 1);
  light.position.set(5, 5, 5);
  scene.add(light);
  scene.add(new THREE.AmbientLight(0x404040));
  const colors = { C: 0x909090, N: 0x3050f8, O: 0xff0d0d, S: 0xffff30, default: 0xff69b4 };
  const atoms = data.atoms;
  const center = atoms.reduce((c, a) => ({ x: c.x + a.x, y: c.y + a.y, z: c.z + a.z }), { x: 0, y: 0, z: 0 });
  center.x /= atoms.length; center.y /= atoms.length; center.z /= atoms.length;
  atoms.forEach((a) => {
    if (a.symbol === "H") return;
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(a.symbol === "C" ? 0.35 : 0.3, 16, 16), new THREE.MeshPhongMaterial({ color: colors[a.symbol] || colors.default }));
    mesh.position.set(a.x - center.x, a.y - center.y, a.z - center.z);
    scene.add(mesh);
  });
  data.bonds.forEach((b) => {
    const a1 = atoms[b.begin], a2 = atoms[b.end];
    if (!a1 || !a2) return;
    const p1 = new THREE.Vector3(a1.x - center.x, a1.y - center.y, a1.z - center.z);
    const p2 = new THREE.Vector3(a2.x - center.x, a2.y - center.y, a2.z - center.z);
    const dir = new THREE.Vector3().subVectors(p2, p1);
    const mesh = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, dir.length(), 8), new THREE.MeshPhongMaterial({ color: 0x666666 }));
    mesh.position.copy(p1).add(p2).multiplyScalar(0.5);
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
    scene.add(mesh);
  });
  camera.position.z = 12;
  renderer.render(scene, camera);
}

function renderConfusionMatrixTable(cm, labels) {
  if (!cm?.length || !labels?.length) return "";
  const header = `<tr><th></th>${labels.map((l) => `<th>Pred ${l}</th>`).join("")}</tr>`;
  const rows = cm.map((row, i) =>
    `<tr><th>Actual ${labels[i]}</th>${row.map((v) => `<td>${v}</td>`).join("")}</tr>`
  ).join("");
  return `<div class="table-scroll"><table class="results-table"><thead>${header}</thead><tbody>${rows}</tbody></table></div>`;
}

function renderFeatureImportanceTable(list) {
  if (!list?.length) return "<p class=\"text-muted\">Not available for this model.</p>";
  return `<div class="table-scroll"><table class="results-table"><thead><tr><th>Rank</th><th>Feature</th><th>Importance</th></tr></thead><tbody>${list.map((item, i) => `<tr><td>${i + 1}</td><td>${item.feature}</td><td>${item.importance}</td></tr>`).join("")}</tbody></table></div>`;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = String(text ?? "");
  return div.innerHTML;
}

async function fetchMlJson(url, form, timeoutMs = 180000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { method: "POST", body: form, signal: controller.signal, cache: "no-store" });
    const text = await response.text();
    let json;
    try {
      json = JSON.parse(text);
    } catch {
      throw new Error(`Server returned non-JSON (HTTP ${response.status}): ${text.slice(0, 500)}`);
    }
    if (!response.ok && json.success !== false) {
      json = { success: false, error: json.detail || json.error || `HTTP ${response.status}` };
    }
    return json;
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("Training timed out after 3 minutes. Try Random Forest, fewer CV folds, or a smaller dataset.");
    }
    if (err.message?.includes("Failed to fetch") || err.message?.includes("NetworkError")) {
      throw new Error("Cannot reach the server. Is Docker running? Open http://localhost:8080 and refresh the page.");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

function renderMlPretrainDebug(preview) {
  const el = document.getElementById("ml-pretrain-debug");
  if (!el || !preview) return;
  const warnings = (preview.warnings || []).map((w) => `<li>${escapeHtml(w)}</li>`).join("");
  el.innerHTML = `
    <h4>Before Training</h4>
    <p><strong>Selected Features:</strong> ${escapeHtml((preview.feature_columns || []).join(", "))}</p>
    <p><strong>Selected Target:</strong> ${escapeHtml(preview.target_column)}</p>
    <p><strong>X Shape:</strong> (${preview.x_shape?.[0] ?? "?"}, ${preview.x_shape?.[1] ?? "?"})</p>
    <p><strong>y Shape:</strong> (${preview.y_shape?.[0] ?? "?"})</p>
    <p><strong>Unique Target Classes:</strong> ${escapeHtml((preview.unique_classes || []).join(", "))}</p>
    ${warnings ? `<ul class="text-muted" style="margin-top:0.5rem;font-size:0.85rem">${warnings}</ul>` : ""}`;
  el.classList.remove("hidden");
}

function renderMlTrainingResults(d) {
  const distRows = Object.entries(d.class_distribution || {})
    .map(([k, v]) => `<tr><td>${escapeHtml(k)}</td><td>${v}</td></tr>`).join("");
  const predRows = (d.predictions || []).slice(0, 20)
    .map((r) => `<tr><td>${escapeHtml(r.actual)}</td><td>${escapeHtml(r.predicted)}</td></tr>`).join("");
  const dbg = d.debug || {};
  const dbgWarnings = (dbg.warnings || []).map((w) => `<li>${escapeHtml(w)}</li>`).join("");

  return `
    <p class="alert alert-success">Model trained successfully.</p>
    <div class="card ml-step"><h3><span class="step-num">7</span> Results Dashboard</h3></div>
    <div class="card"><h3>Dataset Summary</h3>
      <div class="stat-grid">
        ${statBox("Total Rows", d.total_rows ?? d.samples_used)}
        ${statBox("Total Columns", d.total_columns ?? "—")}
        ${statBox("Features", d.n_features)}
        ${statBox("Target", d.target_column)}
      </div>
      <p style="margin-top:0.75rem"><strong>Selected Target Column:</strong> ${escapeHtml(d.target_column)}</p>
      <div style="margin-top:1rem"><strong>Class Distribution</strong>
        <table class="results-table"><thead><tr><th>Class</th><th>Count</th></tr></thead><tbody>${distRows}</tbody></table>
      </div>
    </div>
    <div class="card"><h3>Model Performance</h3>
      <div class="stat-grid">
        ${statBox("Accuracy", d.accuracy)}
        ${statBox("Precision", d.precision)}
        ${statBox("Recall", d.recall)}
        ${statBox("F1 Score", d.f1_score)}
        ${statBox("AUC Score", d.auc ?? "N/A")}
      </div>
      <p class="text-muted" style="margin-top:0.5rem">Model: ${escapeHtml(d.model_name)}</p>
    </div>
    <div class="card"><h3>Classification Report</h3>
      <pre class="code-block" style="white-space:pre-wrap;font-size:0.8rem">${escapeHtml(d.classification_report_text || "")}</pre>
      ${renderClassificationReport(d.classification_report, d.class_labels)}
    </div>
    <div class="card"><h3>Confusion Matrix (Table)</h3>
      ${renderConfusionMatrixTable(d.confusion_matrix, d.confusion_matrix_labels || d.class_labels)}
    </div>
    ${d.confusion_matrix_png ? `<div class="card"><h3>Confusion Matrix (Heatmap)</h3><div class="plot-container"><img src="data:image/png;base64,${d.confusion_matrix_png}" alt="Confusion Matrix"/></div></div>` : ""}
    ${d.roc_curve_png ? `<div class="card"><h3>ROC Curve</h3><p><strong>AUC Score:</strong> ${d.auc ?? "N/A"}</p><div class="plot-container"><img src="data:image/png;base64,${d.roc_curve_png}" alt="ROC"/></div></div>` : `<div class="card"><h3>ROC / AUC</h3><p><strong>AUC Score:</strong> ${d.auc ?? "N/A (multi-class or insufficient data)"}</p></div>`}
    <div class="card"><h3>Prediction Preview (first 20 rows)</h3>
      <div class="table-scroll"><table class="results-table"><thead><tr><th>Actual</th><th>Predicted</th></tr></thead><tbody>${predRows}</tbody></table></div>
    </div>
    <div class="card"><h3>Feature Importance</h3>
      ${renderFeatureImportanceTable(d.feature_importance)}
      ${d.feature_importance_png ? `<div class="plot-container" style="margin-top:1rem"><img src="data:image/png;base64,${d.feature_importance_png}" alt="Feature Importance"/></div>` : ""}
    </div>
    <div class="card"><h3>Downloads</h3>
      <div class="form-row">
        <a href="/api/ml/download" class="btn btn-secondary">trained_model.pkl</a>
        <a href="/api/ml/download-predictions" class="btn btn-secondary">predictions.csv</a>
      </div>
    </div>
    <details class="card ml-debug-details">
      <summary><strong>Debug Information</strong></summary>
      <div style="margin-top:0.75rem;font-size:0.85rem">
        <p><strong>Dataset shape:</strong> ${dbg.dataset_shape?.[0]} rows × ${dbg.dataset_shape?.[1]} columns</p>
        <p><strong>Feature columns:</strong> ${escapeHtml((dbg.feature_columns || []).join(", "))}</p>
        <p><strong>Target column:</strong> ${escapeHtml(dbg.target_column)}</p>
        <p><strong>Model:</strong> ${escapeHtml(dbg.model_name || d.model_name)}</p>
        <p><strong>Train / Test sizes:</strong> ${dbg.train_size} / ${dbg.test_size}</p>
        <p><strong>Test split ratio:</strong> ${dbg.test_split_ratio}</p>
        <p><strong>X shape:</strong> (${dbg.x_shape?.[0]}, ${dbg.x_shape?.[1]})</p>
        <p><strong>y shape:</strong> (${dbg.y_shape?.[0]})</p>
        <p><strong>Unique classes:</strong> ${escapeHtml((dbg.unique_classes || []).join(", "))}</p>
        ${dbgWarnings ? `<p><strong>Warnings:</strong></p><ul>${dbgWarnings}</ul>` : "<p><strong>Warnings:</strong> None</p>"}
      </div>
    </details>`;
}

function showMlTrainingError(message, detail) {
  const resultsWrap = document.getElementById("ml-step-results");
  const results = document.getElementById("ml-results");
  resultsWrap?.classList.remove("hidden");
  results.innerHTML = `
    <div class="card">
      <h3>Training Failed</h3>
      <p class="alert alert-error">${escapeHtml(message)}</p>
      ${detail ? `<details open><summary>Error details</summary><pre class="code-block" style="white-space:pre-wrap;font-size:0.75rem;max-height:320px;overflow:auto">${escapeHtml(detail)}</pre></details>` : ""}
    </div>`;
  resultsWrap?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function refreshMlPretrainDebug() {
  const panel = document.getElementById("ml-pretrain-debug");
  if (!panel || !mlFile || !mlTargetValid) {
    panel?.classList.add("hidden");
    return;
  }
  const features = getSelectedMlFeatures();
  const target = document.getElementById("ml-target-col")?.value;
  const modelType = document.getElementById("ml-model-type")?.value;
  if (!features.length || !target || !modelType) {
    panel.classList.add("hidden");
    return;
  }
  panel.innerHTML = '<p class="loading">Loading training preview…</p>';
  panel.classList.remove("hidden");
  try {
    const form = new FormData();
    form.append("file", mlFile);
    form.append("feature_columns", features.join(","));
    form.append("target_column", target);
    form.append("test_size", document.getElementById("ml-test-size")?.value || "0.2");
    const json = await fetchMlJson("/api/ml/prepare", form);
    if (!json.success) {
      panel.innerHTML = `<p class="alert alert-error">${escapeHtml(json.error)}</p>`;
      return;
    }
    renderMlPretrainDebug(json.data);
  } catch (err) {
    panel.innerHTML = `<p class="alert alert-error">${escapeHtml(err.message)}</p>`;
  }
}
// ——— ML Classifier ———
let mlFile = null;
let mlDataset = null;
let mlTargetValid = false;

const ML_WORKFLOW_STEPS = [
  "ml-step-target",
  "ml-step-features",
  "ml-step-model",
  "ml-step-config",
  "ml-step-train",
];

function hideAllMlWorkflowSteps() {
  ML_WORKFLOW_STEPS.forEach((id) => document.getElementById(id)?.classList.add("hidden"));
  document.getElementById("ml-step-results")?.classList.add("hidden");
  const results = document.getElementById("ml-results");
  if (results) results.innerHTML = "";
}

/** Show workflow steps 1..visibleCount (1=target only, 5=all incl. train) */
function revealMlWorkflow(visibleCount) {
  ML_WORKFLOW_STEPS.forEach((id, i) => {
    document.getElementById(id)?.classList.toggle("hidden", i >= visibleCount);
  });
}

function getSelectedMlFeatures() {
  const sel = document.getElementById("ml-feature-cols");
  if (!sel) return [];
  return [...sel.selectedOptions].map((o) => o.value);
}

function updateMlFeatureOptions(columns, targetCol) {
  const sel = document.getElementById("ml-feature-cols");
  if (!sel) return;
  const features = columns.filter((c) => c !== targetCol);
  sel.innerHTML = features.map((c) => `<option value="${c}">${c}</option>`).join("");
  [...sel.options].forEach((o) => { o.selected = true; });
}

function updateMlTrainButtonState() {
  const btn = document.getElementById("ml-train-btn");
  if (!btn) return;
  const target = document.getElementById("ml-target-col")?.value;
  const features = getSelectedMlFeatures();
  const model = document.getElementById("ml-model-type")?.value;
  btn.disabled = !(mlTargetValid && target && features.length > 0 && model);
}

function onMlFeaturesChanged() {
  const features = getSelectedMlFeatures();
  const hint = document.getElementById("ml-feature-hint");
  if (hint) hint.classList.toggle("hidden", features.length > 0);
  revealMlWorkflow(features.length > 0 ? 3 : 2);
  updateMlTrainButtonState();
}

function onMlModelChanged() {
  if (document.getElementById("ml-model-type")?.value) {
    revealMlWorkflow(5);
    refreshMlPretrainDebug();
  }
  updateMlTrainButtonState();
}

async function validateMlTarget() {
  const target = document.getElementById("ml-target-col")?.value;
  const warnEl = document.getElementById("ml-target-warning");
  const infoEl = document.getElementById("ml-target-info");
  mlTargetValid = false;
  hideAlert("ml-target-warning");
  if (infoEl) { infoEl.classList.add("hidden"); infoEl.innerHTML = ""; }
  updateMlTrainButtonState();

  if (!mlFile || !target) {
    revealMlWorkflow(1);
    return;
  }

  const form = new FormData();
  form.append("file", mlFile);
  form.append("target_column", target);
  let json;
  try {
    json = await fetchMlJson("/api/ml/validate-target", form, 60000);
  } catch (err) {
    showAlert("ml-alert", err.message);
    window.appContext.setLastError(err.message);
    revealMlWorkflow(1);
    return;
  }

  if (!json.success) {
    showAlert("ml-alert", json.error);
    window.appContext.setLastError(json.error);
    revealMlWorkflow(1);
    return;
  }

  const data = json.data;
  if (data.is_continuous) {
    warnEl.textContent = "Selected column appears continuous. Choose a categorical target column for classification.";
    warnEl.classList.remove("hidden");
    window.appContext.setLastError(warnEl.textContent);
    revealMlWorkflow(1);
    return;
  }

  mlTargetValid = true;
  hideAlert("ml-alert");
  renderClassDistribution(data.class_distribution, "ml-target-info");

  window._mlContext = {
    ...(window._mlContext || {}),
    target_column: target,
    class_distribution: data.class_distribution,
  };

  updateMlFeatureOptions(mlDataset.columns, target);
  revealMlWorkflow(2);
  onMlFeaturesChanged();
}

function resetMlWorkflowAfterUpload() {
  mlTargetValid = false;
  hideAllMlWorkflowSteps();
  document.getElementById("ml-target-col").innerHTML =
    '<option value="">— Select target column —</option>' +
    mlDataset.columns.map((c) => `<option value="${c}">${c}</option>`).join("");
  document.getElementById("ml-model-type").value = "";
  document.getElementById("ml-feature-cols").innerHTML = "";
  updateMlTrainButtonState();
}

document.getElementById("ml-file")?.addEventListener("change", async (e) => {
  mlFile = e.target.files[0];
  if (!mlFile) return;

  hideAlert("ml-alert");
  hideAlert("ml-target-warning");
  hideAllMlWorkflowSteps();

  const form = new FormData();
  form.append("file", mlFile);
  const json = await fetchMlJson("/api/ml/preview", form, 60000).catch((err) => ({ success: false, error: err.message }));
  if (!json.success) {
    showAlert("ml-alert", json.error);
    window.appContext.setLastError(json.error);
    return;
  }

  const data = json.data;
  mlDataset = data;

  window._mlContext = {
    columns: data.columns,
    column_stats: data.column_stats,
    numeric_columns: data.numeric_columns,
    categorical_columns: data.categorical_columns,
    shape: data.shape,
    dtypes: data.dtypes,
  };

  renderDatasetInfo(data, "ml-dataset-info");
  renderDtypesTable(data, "ml-dtypes-info");
  renderMissingSummary(data, "ml-missing-info");
  document.getElementById("ml-preview-wrap").innerHTML =
    `<div style="margin-top:1rem"><h4>Dataset Preview (first ${data.preview_rows} rows)</h4>${renderPreviewTable(data.preview, data.columns)}</div>`;
  document.getElementById("ml-preview-wrap").classList.remove("hidden");

  resetMlWorkflowAfterUpload();
  revealMlWorkflow(1);

  // Auto-select Toxicity/class target when present (user can change)
  const targetSel = document.getElementById("ml-target-col");
  const lower = data.columns.map((c) => c.toLowerCase());
  if (lower.includes("toxicity")) {
    targetSel.value = data.columns[lower.indexOf("toxicity")];
    await validateMlTarget();
  } else if (lower.includes("class")) {
    targetSel.value = data.columns[lower.indexOf("class")];
    await validateMlTarget();
  }
});

document.getElementById("ml-target-col")?.addEventListener("change", validateMlTarget);
document.getElementById("ml-feature-cols")?.addEventListener("change", onMlFeaturesChanged);
document.getElementById("ml-model-type")?.addEventListener("change", onMlModelChanged);

document.getElementById("ml-train-btn")?.addEventListener("click", async () => {
  hideAlert("ml-alert");
  if (!mlFile) { showAlert("ml-alert", "Upload a dataset first."); return; }
  if (!mlTargetValid) { showAlert("ml-alert", "Select a valid target column first."); return; }

  const features = getSelectedMlFeatures();
  const target = document.getElementById("ml-target-col").value;
  const modelType = document.getElementById("ml-model-type").value;

  if (!target) { showAlert("ml-alert", "Select a target column."); return; }
  if (!features.length) { showAlert("ml-alert", "Select at least one feature column."); return; }
  if (!modelType) { showAlert("ml-alert", "Select a model type."); return; }
  if (features.includes(target)) { showAlert("ml-alert", "Target column cannot be a feature."); return; }

  const form = new FormData();
  form.append("file", mlFile);
  form.append("feature_columns", features.join(","));
  form.append("target_column", target);
  form.append("model_type", modelType);
  form.append("test_size", document.getElementById("ml-test-size").value || "0.2");
  form.append("random_state", document.getElementById("ml-random-state").value || "42");
  form.append("cv_folds", document.getElementById("ml-cv-folds").value || "5");

  const resultsWrap = document.getElementById("ml-step-results");
  const results = document.getElementById("ml-results");
  resultsWrap.classList.remove("hidden");
  results.innerHTML = '<p class="loading">Training model… This may take up to 2 minutes.</p>';
  resultsWrap.scrollIntoView({ behavior: "smooth", block: "start" });

  const trainBtn = document.getElementById("ml-train-btn");
  if (trainBtn) trainBtn.disabled = true;

  try {
    const json = await fetchMlJson("/api/ml/train", form, 180000);
    if (!json.success) {
      const errMsg = json.error || "Training failed.";
      showAlert("ml-alert", errMsg);
      window.appContext.setLastError(errMsg);
      showMlTrainingError(errMsg, json.detail || null);
      return;
    }
    if (!json.data) {
      showMlTrainingError("Training returned no data.", null);
      return;
    }
    results.innerHTML = renderMlTrainingResults(json.data);
    document.getElementById("ml-status-badge").textContent = "Model loaded";
    document.getElementById("ml-status-badge").className = "badge badge-success";
  } catch (err) {
    const msg = err.message || String(err);
    showAlert("ml-alert", msg);
    window.appContext.setLastError(msg);
    showMlTrainingError(msg, err.stack || null);
  } finally {
    updateMlTrainButtonState();
  }
});

// ——— Visualization ———
let vizFile = null;

function updateVizFields() {
  const t = document.getElementById("viz-plot-type").value;
  const scatter = ["scatter", "line", "bar", "histogram"];
  document.getElementById("viz-scatter-fields").classList.toggle("hidden", !scatter.includes(t));
  document.getElementById("viz-multi-fields").classList.toggle("hidden", !["heatmap", "boxplot", "correlation_matrix"].includes(t));
}

document.getElementById("viz-plot-type")?.addEventListener("change", updateVizFields);

document.getElementById("viz-file")?.addEventListener("change", async (e) => {
  vizFile = e.target.files[0];
  if (!vizFile) return;
  const form = new FormData();
  form.append("file", vizFile);
  const json = await (await fetch("/api/viz/preview", { method: "POST", body: form })).json();
  if (!json.success) { showAlert("viz-alert", json.error); return; }
  hideAlert("viz-alert");
  const data = json.data;
  window._vizContext = {
    columns: data.columns,
    numeric_columns: data.numeric_columns,
    categorical_columns: data.categorical_columns,
  };
  renderDatasetInfo(data, "viz-dataset-info");
  document.getElementById("viz-preview-wrap").innerHTML = `<div class="card"><h3>Dataset Preview</h3>${renderPreviewTable(data.preview, data.columns)}</div>`;
  document.getElementById("viz-preview-wrap").classList.remove("hidden");
  const fill = (id, cols) => { document.getElementById(id).innerHTML = '<option value="">—</option>' + cols.map((c) => `<option value="${c}">${c}</option>`).join(""); };
  fill("viz-x", data.columns);
  fill("viz-y", data.columns);
  fill("viz-color", data.columns);
  document.getElementById("viz-multi-cols").innerHTML = data.numeric_columns.map((c) => `<label class="checkbox-inline"><input type="checkbox" name="viz-multi-col" value="${c}" checked/> ${c}</label>`).join("");
  updateVizFields();
});

document.getElementById("viz-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAlert("viz-alert");
  if (!vizFile) { showAlert("viz-alert", "Upload a CSV first."); return; }
  const plotType = document.getElementById("viz-plot-type").value;
  const form = new FormData();
  form.append("file", vizFile);
  form.append("plot_type", plotType);
  form.append("x_column", document.getElementById("viz-x").value);
  form.append("y_column", document.getElementById("viz-y").value);
  form.append("color_column", document.getElementById("viz-color").value);
  if (["heatmap", "boxplot", "correlation_matrix"].includes(plotType)) {
    const checked = [...document.querySelectorAll('input[name="viz-multi-col"]:checked')].map((el) => el.value);
    form.append("columns", checked.join(","));
  }
  const results = document.getElementById("viz-results");
  results.innerHTML = '<p class="loading">Generating plot…</p>';
  const json = await (await fetch("/api/viz/plot", { method: "POST", body: form })).json();
  if (!json.success) { showAlert("viz-alert", json.error); results.innerHTML = ""; return; }
  results.innerHTML = renderPlotResult(json.data);
  mountPlotly("plotly-chart", json.data.plotly_json);
});

// ——— GO Enrichment ———
let goResultsCsv = null;

document.getElementById("go-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAlert("go-alert");
  const form = new FormData();
  form.append("genes_text", document.getElementById("go-genes").value);
  const file = document.getElementById("go-file").files[0];
  if (file) form.append("file", file);
  const results = document.getElementById("go-results");
  results.innerHTML = '<p class="loading">Running GO enrichment…</p>';
  const json = await (await fetch("/api/go/enrich", { method: "POST", body: form })).json();
  if (!json.success) { showAlert("go-alert", json.error); results.innerHTML = ""; return; }
  const d = json.data;
  goResultsCsv = d.export_csv;
  results.innerHTML = `
    <div class="card"><h3>Input: ${d.input_gene_count} genes</h3><p class="code-block">${d.genes.join(", ")}</p></div>
    ${d.chart_png ? `<div class="card"><h3>Enrichment Plot</h3><div class="plot-container"><img src="data:image/png;base64,${d.chart_png}" alt="GO plot"/></div></div>` : ""}
    <div class="card"><h3>Enriched GO Terms (${d.result_count})</h3>
      <button type="button" id="go-export-btn" class="btn btn-secondary" style="margin-bottom:1rem">Export CSV</button>
      <div class="table-scroll"><table class="results-table"><thead><tr><th>GO Term</th><th>P-value</th><th>Adj. P-value</th><th>Gene Count</th><th>Genes</th></tr></thead>
      <tbody>${d.results.map((r) => `<tr><td>${r.go_term}</td><td>${r.p_value?.toExponential(2) ?? "—"}</td><td>${r.adjusted_p_value?.toExponential(2) ?? "—"}</td><td>${r.gene_count}</td><td style="font-size:0.75rem">${r.genes}</td></tr>`).join("")}</tbody></table></div>
    </div>`;
  document.getElementById("go-export-btn")?.addEventListener("click", () => {
    const blob = new Blob([goResultsCsv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "go_enrichment_results.csv";
    a.click();
  });
});

// ——— Disease Prediction ———
document.getElementById("disease-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAlert("disease-alert");
  const query = document.getElementById("disease-query").value.trim();
  if (!query) return;
  const results = document.getElementById("disease-results");
  results.innerHTML = '<p class="loading">Analyzing query…</p>';
  const json = await postJSON("/api/disease/predict", { query });
  if (!json.success) { showAlert("disease-alert", json.error); results.innerHTML = ""; return; }
  const d = json.data;
  const p = d.primary_prediction;
  results.innerHTML = `
    <div class="card"><h3>Primary Prediction</h3>
      <h4 class="disease-name">${p.disease}</h4>
      <p><span class="badge badge-success">Confidence: ${(p.confidence_score * 100).toFixed(1)}%</span> · ${p.category}</p>
      <p><strong>Description:</strong> ${p.description}</p>
      <p><strong>Symptoms:</strong> ${p.symptoms}</p>
      <a href="${p.google_search_url}" target="_blank" rel="noopener" class="btn btn-primary" style="margin-top:1rem;display:inline-block">Search on Google</a>
    </div>
    ${d.alternatives.length ? `<div class="card"><h3>Alternative Matches</h3><table class="results-table"><thead><tr><th>Disease</th><th>Score</th><th>Link</th></tr></thead><tbody>${d.alternatives.map((a) => `<tr><td>${a.disease}</td><td>${(a.confidence_score * 100).toFixed(1)}%</td><td><a href="${a.google_search_url}" target="_blank" rel="noopener">Google</a></td></tr>`).join("")}</tbody></table></div>` : ""}`;
});

// ML status on load
fetch("/api/ml/status").then((r) => r.json()).then((json) => {
  if (json.trained) {
    const el = document.getElementById("ml-status-badge");
    if (el) { el.textContent = "Model loaded"; el.className = "badge badge-success"; }
  }
});

updateVizFields();
