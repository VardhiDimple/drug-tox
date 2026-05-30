/**
 * DRUG TOX PRO — frontend dashboard v2
 */

const panels = document.querySelectorAll(".panel");
const navButtons = document.querySelectorAll(".nav-btn");

function navigateTo(panelId) {
  navButtons.forEach((b) => b.classList.toggle("active", b.dataset.panel === panelId));
  panels.forEach((p) => p.classList.toggle("active", p.id === `panel-${panelId}`));
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
    <p><strong>Shape:</strong> ${data.shape.rows} rows × ${data.shape.columns} columns</p>
    <p><strong>Columns:</strong> ${data.columns.join(", ")}</p>
  `;
  el.classList.remove("hidden");
}

function renderClassificationReport(report, labels) {
  let rows = "";
  for (const label of labels) {
    const r = report[label];
    if (!r || typeof r !== "object") continue;
    rows += `<tr><td>${label}</td><td>${(r.precision ?? 0).toFixed(3)}</td><td>${(r.recall ?? 0).toFixed(3)}</td><td>${(r.f1-score ?? 0).toFixed(3)}</td><td>${r.support ?? 0}</td></tr>`;
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

// ——— ML Classifier ———
let mlFile = null;

document.getElementById("ml-file")?.addEventListener("change", async (e) => {
  mlFile = e.target.files[0];
  if (!mlFile) return;
  const form = new FormData();
  form.append("file", mlFile);
  const json = await (await fetch("/api/ml/preview", { method: "POST", body: form })).json();
  if (!json.success) { showAlert("ml-alert", json.error); return; }
  hideAlert("ml-alert");
  const data = json.data;
  renderDatasetInfo(data, "ml-dataset-info");
  document.getElementById("ml-preview-wrap").innerHTML = `<div class="card"><h3>Dataset Preview</h3>${renderPreviewTable(data.preview, data.columns)}</div>`;
  document.getElementById("ml-preview-wrap").classList.remove("hidden");
  const featSel = document.getElementById("ml-feature-cols");
  const targetSel = document.getElementById("ml-target-col");
  featSel.innerHTML = data.columns.map((c) => `<option value="${c}">${c}</option>`).join("");
  targetSel.innerHTML = data.columns.map((c) => `<option value="${c}">${c}</option>`).join("");
  const lower = data.columns.map((c) => c.toLowerCase());
  if (lower.includes("smiles")) Array.from(featSel.options).find((o) => o.value.toLowerCase() === "smiles").selected = true;
  if (lower.includes("class")) targetSel.value = data.columns[lower.indexOf("class")];
  document.getElementById("ml-column-select").classList.remove("hidden");
});

document.getElementById("ml-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAlert("ml-alert");
  if (!mlFile) { showAlert("ml-alert", "Upload a CSV file first."); return; }
  const features = [...document.getElementById("ml-feature-cols").selectedOptions].map((o) => o.value);
  const target = document.getElementById("ml-target-col").value;
  if (!features.length) { showAlert("ml-alert", "Select at least one feature column."); return; }
  const form = new FormData();
  form.append("file", mlFile);
  form.append("feature_columns", features.join(","));
  form.append("target_column", target);
  form.append("test_size", document.getElementById("ml-test-size").value || "0.2");
  const results = document.getElementById("ml-results");
  results.innerHTML = '<p class="loading">Training model…</p>';
  const json = await (await fetch("/api/ml/train", { method: "POST", body: form })).json();
  if (!json.success) { showAlert("ml-alert", json.error); results.innerHTML = ""; return; }
  const d = json.data;
  results.innerHTML = `
    <div class="card"><h3>Training Results</h3>
      <div class="stat-grid">${statBox("Accuracy", (d.accuracy * 100).toFixed(1) + "%")}${statBox("AUC", d.auc ?? "N/A")}${statBox("Samples", d.samples_used)}${statBox("Mode", d.training_mode)}</div>
      <p class="alert alert-success" style="margin-top:1rem">${d.model_ready_for_admet ? "SMILES model ready for ADMET toxicity." : "Tabular model trained successfully."}</p>
      <a href="/api/ml/download" class="btn btn-secondary" style="margin-top:0.75rem;display:inline-block">Download Model (.joblib)</a>
    </div>
    <div class="card"><h3>Classification Report</h3>${renderClassificationReport(d.classification_report, d.class_labels)}</div>
    <div class="grid-2">
      ${d.confusion_matrix_png ? `<div class="card"><h3>Confusion Matrix</h3><div class="plot-container"><img src="data:image/png;base64,${d.confusion_matrix_png}" alt="CM"/></div></div>` : ""}
      ${d.roc_curve_png ? `<div class="card"><h3>ROC Curve</h3><div class="plot-container"><img src="data:image/png;base64,${d.roc_curve_png}" alt="ROC"/></div></div>` : ""}
    </div>`;
  document.getElementById("ml-status-badge").textContent = "Model loaded";
  document.getElementById("ml-status-badge").className = "badge badge-success";
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
