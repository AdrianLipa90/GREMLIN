"use strict";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const SVG_NS = "http://www.w3.org/2000/svg";
const MAX_ACTIVITY = 12;
const TECHNICAL_MODE_STORAGE_KEY = "gremlin.workspace.technical-mode";

const candidateEditor = $("#candidate-editor");
const problemBrief = $("#problem-brief");
const sampleCount = $("#sample-count");
const runButton = $("#run-candidate");
const loadButton = $("#load-example");
const runStatus = $("#run-status");
const verdict = $("#verdict");
const inputState = $("#input-state");
const footerMessage = $("#footer-message");
const technicalToggle = $("#technical-toggle");
const refreshSystemButton = $("#refresh-system");
const retryErrorButton = $("#retry-error");
const activityList = $("#activity-list");
const clearActivityButton = $("#clear-activity");

const productBadge = $("#product-badge");
const mcpBadge = $("#mcp-badge");
const systemLoadState = $("#system-load-state");
const systemProductStatus = $("#system-product-status");
const systemEdition = $("#system-edition");
const systemToolCount = $("#system-tool-count");
const systemContract = $("#system-contract");
const systemSpeciesCount = $("#system-species-count");
const systemAuthority = $("#system-authority");
const bestiaryTopology = $("#bestiary-topology");
const bestiaryGrid = $("#bestiary-grid");

const sessionState = {
  activity: [],
  technical: false,
};

function pretty(value) {
  return JSON.stringify(value, null, 2);
}


function nowLabel() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function recordActivity(kind, message) {
  sessionState.activity.unshift({
    kind: ["pass", "fail", "info"].includes(kind) ? kind : "info",
    message: String(message),
    time: nowLabel(),
  });
  sessionState.activity = sessionState.activity.slice(0, MAX_ACTIVITY);
  renderActivity();
}

function renderActivity() {
  activityList.replaceChildren();
  if (!sessionState.activity.length) {
    const empty = document.createElement("li");
    empty.className = "activity-empty";
    empty.textContent = "No activity yet.";
    activityList.appendChild(empty);
    return;
  }
  sessionState.activity.forEach((item) => {
    const row = document.createElement("li");
    row.className = item.kind;
    const timeNode = document.createElement("span");
    timeNode.className = "activity-time";
    timeNode.textContent = item.time;
    const messageNode = document.createElement("span");
    messageNode.className = "activity-message";
    messageNode.textContent = item.message;
    row.append(timeNode, messageNode);
    activityList.appendChild(row);
  });
}

function readTechnicalModePreference() {
  try {
    return window.sessionStorage.getItem(TECHNICAL_MODE_STORAGE_KEY) === "true";
  } catch (_) {
    return false;
  }
}

function persistTechnicalModePreference(enabled) {
  try {
    window.sessionStorage.setItem(TECHNICAL_MODE_STORAGE_KEY, enabled ? "true" : "false");
  } catch (_) {
    // Optional preference storage must never block Workspace operation.
  }
}

function setTechnicalMode(enabled, { persist = true } = {}) {
  sessionState.technical = Boolean(enabled);
  document.body.classList.toggle("technical-mode", sessionState.technical);
  technicalToggle.setAttribute("aria-pressed", sessionState.technical ? "true" : "false");
  technicalToggle.textContent = sessionState.technical ? "Reader view" : "Technical view";
  if (persist) persistTechnicalModePreference(sessionState.technical);

  if (!sessionState.technical) {
    const active = $(".tab.active");
    if (active && active.classList.contains("technical-only")) {
      const prototypeTab = $('.tab[data-tab="prototype"]');
      if (prototypeTab) prototypeTab.click();
    }
  }
}

class WorkspaceHttpError extends Error {
  constructor(message, { status, payload, url }) {
    super(message);
    this.name = "WorkspaceHttpError";
    this.status = status;
    this.payload = payload;
    this.url = url;
  }

  get contract() {
    return this.payload?.error_contract || null;
  }
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    cache: "no-store",
    ...options,
  });
  let payload;
  try {
    payload = await response.json();
  } catch (_) {
    throw new WorkspaceHttpError(
      `Invalid JSON response from ${url} (HTTP ${response.status})`,
      { status: response.status, payload: null, url },
    );
  }
  if (!response.ok) {
    const contract = payload?.error_contract || null;
    const message =
      contract?.detail_code ||
      payload?.error ||
      payload?.reason ||
      `HTTP ${response.status}`;
    throw new WorkspaceHttpError(message, {
      status: response.status,
      payload,
      url,
    });
  }
  return payload;
}

function clearErrorGuidance() {
  const guidance = $("#error-guidance");
  guidance.hidden = true;
  $("#error-code").textContent = "ERROR";
  $("#error-action").textContent = "Inspect GREMLIN Diagnostics before retrying.";
  $("#error-retry").textContent = "";
  retryErrorButton.hidden = true;
  retryErrorButton.disabled = false;
}

function showErrorGuidance(error) {
  const guidance = $("#error-guidance");
  const contract = error instanceof WorkspaceHttpError ? error.contract : null;
  if (!contract) {
    guidance.hidden = true;
    return null;
  }
  $("#error-code").textContent = contract.error_code || "ERROR";
  $("#error-action").textContent =
    contract.user_action || "Inspect GREMLIN Diagnostics before retrying.";
  $("#error-retry").textContent = contract.retryable ? "retryable" : "manual action";
  retryErrorButton.hidden = contract.retryable !== true;
  retryErrorButton.disabled = false;
  guidance.hidden = false;
  guidance.focus();
  return contract;
}

function setBadge(element, text, state = "") {
  element.className = "badge";
  if (state) element.classList.add(state);
  element.textContent = text;
}

function renderBestiary(bestiary) {
  bestiaryGrid.replaceChildren();
  const species = Array.isArray(bestiary?.species) ? bestiary.species : [];
  species.forEach((item) => {
    const card = document.createElement("article");
    card.className = `beast-card beast-stage-${String(item.stage || "unknown").toLowerCase()}`;

    const head = document.createElement("div");
    head.className = "beast-head";

    const name = document.createElement("strong");
    name.textContent = item.name || "UNKNOWN";

    const stage = document.createElement("span");
    stage.className = "beast-stage";
    stage.textContent = item.stage || "unknown";

    const role = document.createElement("p");
    role.textContent = item.role || "No role description.";

    head.append(name, stage);
    card.append(head, role);
    bestiaryGrid.appendChild(card);
  });

  const topology = Array.isArray(bestiary?.topology) ? bestiary.topology : [];
  bestiaryTopology.textContent = topology.length ? topology.join(" → ") : "topology unavailable";
}

function renderSystem(payload) {
  const product = payload.product || {};
  const license = product.license || {};
  const mcp = payload.mcp || {};
  const bestiary = payload.bestiary || {};
  const authority = payload.authority || {};

  const productStatus = String(product.status || "UNKNOWN");
  systemProductStatus.textContent = productStatus.replaceAll("_", " ");
  systemEdition.textContent = license.edition ? `edition ${license.edition}` : "edition —";

  const toolCount = Number.isInteger(mcp.tool_count) ? mcp.tool_count : "—";
  systemToolCount.textContent = toolCount === "—" ? "—" : `${toolCount} tools`;
  systemContract.textContent = mcp.capability_contract || "contract —";

  const speciesCount = Number.isInteger(bestiary.species_count) ? bestiary.species_count : "—";
  systemSpeciesCount.textContent = speciesCount === "—" ? "—" : `${speciesCount} roles`;

  const closed = authority.production_runtime_write === false
    && authority.execution_admitted === false
    && authority.canon_allowed === false;
  systemAuthority.textContent = closed ? "CLOSED" : "CHECK REQUIRED";

  setBadge(
    productBadge,
    `product: ${productStatus.toLowerCase().replaceAll("_", " ")}`,
    productStatus === "LICENSED" ? "badge-safe" : "badge-muted",
  );
  setBadge(
    mcpBadge,
    `MCP: ${toolCount === "—" ? "unknown" : toolCount + " tools"}`,
    toolCount === 29 ? "badge-safe" : "badge-muted",
  );

  renderBestiary(bestiary);
  systemLoadState.className = "run-status pass";
  systemLoadState.textContent = "system verified";
}

async function loadSystem({ record = false } = {}) {
  systemLoadState.className = "run-status running";
  systemLoadState.textContent = "loading system…";
  try {
    const payload = await fetchJson("/api/system");
    renderSystem(payload);
    if (record) recordActivity("info", "System and Bestiary state refreshed.");
  } catch (error) {
    systemLoadState.className = "run-status fail";
    systemLoadState.textContent = "system unavailable";
    setBadge(productBadge, "product: unavailable", "badge-muted");
    setBadge(mcpBadge, "MCP: unavailable", "badge-muted");
    bestiaryTopology.textContent = String(error.message || error);
    bestiaryGrid.replaceChildren();
    if (record) recordActivity("fail", `System refresh failed: ${error.message || error}`);
  }
}

function setRunState(state, message) {
  runStatus.className = "run-status";
  if (state) runStatus.classList.add(state);
  runStatus.textContent = message;
  footerMessage.textContent = message;
}

function setVerdict(status) {
  verdict.className = "verdict";
  if (status === "VALIDATED_PROTOTYPE") {
    verdict.classList.add("verdict-pass");
    verdict.textContent = "VALIDATED PROTOTYPE";
  } else if (status) {
    verdict.classList.add("verdict-fail");
    verdict.textContent = status.replaceAll("_", " ");
  } else {
    verdict.classList.add("verdict-idle");
    verdict.textContent = "NO RUN";
  }
}

function markCandidate(valid) {
  inputState.className = "state-dot";
  inputState.classList.add(valid ? "valid" : "invalid");
}

function parseCandidate() {
  const value = JSON.parse(candidateEditor.value);
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Candidate must be a JSON object.");
  }
  return value;
}

function buildRequest(candidate) {
  const count = Number.parseInt(sampleCount.value, 10);
  if (!Number.isInteger(count) || count < 1 || count > 512) {
    throw new Error("Reference samples must be an integer in 1..512.");
  }
  return {
    schema: "GREMLIN_CLIENT_PROTOTYPE_REQUEST_V0_1",
    request_id: `visual-${Date.now()}`,
    target: "python_reference",
    sample_count: count,
    candidate,
  };
}

async function loadExample() {
  setRunState("running", "loading example…");
  try {
    const request = await fetchJson("/api/example");
    candidateEditor.value = pretty(request.candidate);
    sampleCount.value = request.sample_count || 64;
    if (!problemBrief.value.trim()) {
      problemBrief.value = "Inspect the supplied phase-native relations, compile their invariant structure into PhaseNav character IR, build a reference prototype and attempt to falsify its numerical conformance.";
    }
    markCandidate(true);
    setRunState("", "example loaded");
    recordActivity("info", "Example candidate loaded.");
  } catch (error) {
    markCandidate(false);
    setRunState("fail", String(error.message || error));
    recordActivity("fail", `Example load failed: ${error.message || error}`);
  }
}

function setPipeline(stages) {
  const active = new Set(stages || []);
  $$(".pipeline-stage").forEach((element) => {
    element.classList.toggle("active", active.has(element.textContent.trim()));
  });
}

function svgElement(name, attrs = {}) {
  const node = document.createElementNS(SVG_NS, name);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
  return node;
}

function svgText(parent, x, y, text, className, anchor = "start") {
  const node = svgElement("text", { x, y, class: className, "text-anchor": anchor });
  node.textContent = text;
  parent.appendChild(node);
  return node;
}

function drawRoundedNode(svg, x, y, width, height, className, label, sublabel = "") {
  const group = svgElement("g");
  const rect = svgElement("rect", { x, y, width, height, rx: 10, class: className });
  group.appendChild(rect);
  svgText(group, x + width / 2, y + (sublabel ? 22 : 27), label, "graph-label", "middle");
  if (sublabel) svgText(group, x + width / 2, y + 39, sublabel, "graph-sub", "middle");
  svg.appendChild(group);
  return group;
}

function truncate(text, max = 24) {
  const value = String(text || "");
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

function renderGraph(ir) {
  const svg = $("#operator-graph");
  while (svg.firstChild) svg.removeChild(svg.firstChild);

  const terms = Array.isArray(ir?.terms) ? ir.terms : [];
  if (!terms.length) {
    svg.setAttribute("viewBox", "0 0 840 480");
    svgText(svg, 420, 235, "No character terms in the returned IR.", "svg-empty", "middle");
    return;
  }

  const rowHeight = 150;
  const top = 40;
  const height = Math.max(480, top * 2 + terms.length * rowHeight);
  svg.setAttribute("viewBox", `0 0 840 ${height}`);

  terms.forEach((term, index) => {
    const centerY = top + index * rowHeight + 58;
    const activeLanes = term.ell
      .map((coefficient, lane) => ({ lane, coefficient }))
      .filter((item) => item.coefficient !== 0);

    const operatorX = 300;
    const operatorY = centerY - 30;
    const operatorW = 255;
    const operatorH = 60;
    const sourceX = 635;
    const sourceY = centerY - 25;
    const sourceW = 170;
    const sourceH = 50;

    const laneSpacing = Math.min(42, 92 / Math.max(1, activeLanes.length));
    const laneStartY = centerY - ((activeLanes.length - 1) * laneSpacing) / 2;

    activeLanes.forEach((item, laneIndex) => {
      const laneY = laneStartY + laneIndex * laneSpacing;
      const edge = svgElement("line", {
        x1: 190,
        y1: laneY,
        x2: operatorX,
        y2: centerY,
        class: "graph-edge accent",
      });
      svg.appendChild(edge);
      drawRoundedNode(
        svg,
        32,
        laneY - 18,
        158,
        36,
        "graph-lane",
        `θ${item.lane}`,
        `ell=${item.coefficient}`,
      );
    });

    const sourceEdge = svgElement("line", {
      x1: operatorX + operatorW,
      y1: centerY,
      x2: sourceX,
      y2: centerY,
      class: "graph-edge",
    });
    svg.appendChild(sourceEdge);

    drawRoundedNode(
      svg,
      operatorX,
      operatorY,
      operatorW,
      operatorH,
      "graph-term",
      `Kχ / ${term.kind || "character"}`,
      `g=${truncate(term.gain_f64_hex, 19)}  τ=${truncate(term.tau_f64_hex, 19)}`,
    );
    drawRoundedNode(
      svg,
      sourceX,
      sourceY,
      sourceW,
      sourceH,
      "graph-source",
      truncate(term.source_ref || `term-${index + 1}`, 20),
      `term ${index + 1}`,
    );
  });
}

function renderTestGrid(receipt) {
  const grid = $("#test-grid");
  grid.replaceChildren();
  const tests = receipt?.tests || {};
  Object.entries(tests).forEach(([name, result]) => {
    const card = document.createElement("div");
    card.className = `test-card ${result === "PASS" ? "pass" : "fail"}`;
    const label = document.createElement("span");
    label.className = "name";
    label.textContent = name;
    const value = document.createElement("span");
    value.className = "result";
    value.textContent = result;
    card.append(label, value);
    grid.appendChild(card);
  });
}

function renderResponse(wrapper, candidate) {
  clearErrorGuidance();
  const response = wrapper.response;
  const artifacts = response.artifacts || {};
  const ir = artifacts.phasenav_ir || {};
  const prototype = artifacts.prototype || {};
  const receipt = artifacts.experiment_receipt || {};

  setPipeline(response.pipeline || []);
  setVerdict(response.status);
  renderGraph(ir);

  $("#ir-operator").textContent = ir.operator || "—";
  $("#ir-terms").textContent = Array.isArray(ir.terms) ? String(ir.terms.length) : "—";
  $("#ir-commitment").textContent = ir.ir_commitment || "—";
  $("#ir-commitment").title = ir.ir_commitment || "";
  $("#response-commitment").textContent = response.response_commitment || "—";
  $("#response-commitment").title = response.response_commitment || "";

  $("#prototype-status").textContent = prototype.status || "UNTRUSTED_PROTOTYPE";
  $("#prototype-commitment").textContent = prototype.prototype_commitment || "—";
  $("#prototype-source").textContent = prototype.source || "No prototype source returned.";

  $("#audit-view").textContent = pretty({
    candidate_id: candidate.candidate_id,
    candidate_status: candidate.status,
    audit: candidate.audit || {},
    compiler_status: ir.status,
    canon_allowed: response.canon_allowed,
    execution_admitted: response.execution_admitted,
  });

  renderTestGrid(receipt);
  $("#test-detail").textContent = pretty({
    validation_scope: receipt.validation_scope,
    sample_count: receipt.sample_count,
    tolerance: receipt.tolerance,
    max_potential_abs_error: receipt.max_potential_abs_error,
    max_force_abs_error: receipt.max_force_abs_error,
    receipt_id: receipt.receipt_id,
  });
  $("#receipt-view").textContent = pretty(receipt);

  const passed = response.status === "VALIDATED_PROTOTYPE";
  setRunState(passed ? "pass" : "fail", passed ? "reference conformance PASS" : String(response.status || "FAIL"));
}

function renderError(error) {
  setPipeline([]);
  setVerdict("ERROR");
  const contract = showErrorGuidance(error);
  const message = String(error.message || error);
  const userAction = contract?.user_action || null;
  const display = userAction ? `${message}\n\nNext action: ${userAction}` : message;
  $("#prototype-source").textContent = display;
  $("#audit-view").textContent = "The candidate or request failed before a validated prototype receipt was produced.";
  $("#test-grid").replaceChildren();
  $("#test-detail").textContent = userAction || message;
  $("#receipt-view").textContent = contract ? pretty(contract) : "No machine-readable error receipt produced.";
  setRunState("fail", contract?.error_code ? `${contract.error_code}: ${userAction || message}` : message);
}

async function runCandidate() {
  runButton.disabled = true;
  markCandidate(true);
  setRunState("running", "compiling → prototyping → testing…");
  try {
    const candidate = parseCandidate();
    const request = buildRequest(candidate);
    const payload = await fetchJson("/api/prototype", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    renderResponse(payload, candidate);
    recordActivity(
      payload.response?.status === "VALIDATED_PROTOTYPE" ? "pass" : "fail",
      `${candidate.candidate_id || "candidate"}: ${payload.response?.status || "completed"}`,
    );
  } catch (error) {
    markCandidate(false);
    renderError(error);
    const contract = error instanceof WorkspaceHttpError ? error.contract : null;
    recordActivity(
      "fail",
      `${contract?.error_code || error.message || error}${contract?.user_action ? ` — ${contract.user_action}` : ""}`,
    );
  } finally {
    runButton.disabled = false;
    retryErrorButton.disabled = false;
  }
}

candidateEditor.addEventListener("input", () => {
  try {
    parseCandidate();
    markCandidate(true);
  } catch (_) {
    markCandidate(false);
  }
});

runButton.addEventListener("click", runCandidate);
loadButton.addEventListener("click", loadExample);
technicalToggle.addEventListener("click", () => setTechnicalMode(!sessionState.technical));
refreshSystemButton.addEventListener("click", async () => {
  refreshSystemButton.disabled = true;
  const label = refreshSystemButton.textContent;
  refreshSystemButton.textContent = "Refreshing…";
  try {
    await loadSystem({ record: true });
  } finally {
    refreshSystemButton.disabled = false;
    refreshSystemButton.textContent = label || "Refresh";
  }
});
retryErrorButton.addEventListener("click", runCandidate);
clearActivityButton.addEventListener("click", () => {
  sessionState.activity = [];
  renderActivity();
});
document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && !runButton.disabled) {
    event.preventDefault();
    runCandidate();
  }
});

$(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    $$(".tab").forEach((node) => node.classList.remove("active"));
    $$(".tab-panel").forEach((node) => node.classList.remove("active"));
    button.classList.add("active");
    $(`#tab-${button.dataset.tab}`).classList.add("active");
  });
});

setTechnicalMode(readTechnicalModePreference(), { persist: false });
renderActivity();
Promise.allSettled([loadSystem(), loadExample()]).then(() => {
  if (footerMessage.textContent === "Ready.") {
    footerMessage.textContent = "Workspace ready.";
  }
});
