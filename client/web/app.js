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
const refreshCockpitButton = $("#refresh-cockpit");
const retryErrorButton = $("#retry-error");
const activityList = $("#activity-list");
const clearActivityButton = $("#clear-activity");

const sessionState = {
  activity: [],
  technical: false,
  health: null,
  product: null,
  capabilities: null,
  bestiary: null,
};

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function text(value, fallback = "—") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
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
    verdict.textContent = String(status).replaceAll("_", " ");
  } else {
    verdict.classList.add("verdict-idle");
    verdict.textContent = "NO RUN";
  }
}

function markCandidate(valid) {
  inputState.className = "state-dot";
  inputState.classList.add(valid ? "valid" : "invalid");
}

function setMetric(selector, value, state = "") {
  const node = $(selector);
  node.textContent = text(value);
  node.className = "";
  if (state) node.classList.add(state);
}

function setBadge(selector, label, kind = "muted") {
  const node = $(selector);
  node.className = "badge";
  node.classList.add(
    kind === "safe" ? "badge-safe" :
    kind === "lock" ? "badge-lock" :
    "badge-muted",
  );
  node.textContent = label;
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
    // Preference storage is optional. Never block Workspace operation on it.
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
      prototypeTab.click();
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

  get errorCode() {
    return this.contract?.error_code || null;
  }

  get userAction() {
    return this.contract?.user_action || null;
  }

  get retryable() {
    return this.contract?.retryable === true;
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

function authorityClosed(authority) {
  return Boolean(
    authority &&
    authority.production_runtime_write === false &&
    authority.execution_admitted === false &&
    authority.canon_allowed === false
  );
}

function renderSystemCockpit() {
  const health = sessionState.health;
  const product = sessionState.product;
  const capabilities = sessionState.capabilities;

  if (health) {
    const ready = health.status === "READY";
    setMetric("#workspace-state", health.status, ready ? "ok" : "fail");
  } else {
    setMetric("#workspace-state", "UNAVAILABLE", "fail");
  }

  if (product) {
    const licensed = product.status === "LICENSED";
    setMetric("#product-state", product.status, licensed ? "ok" : "warn");
    setBadge("#product-badge", `product: ${product.status}`, licensed ? "safe" : "muted");
  } else {
    setMetric("#product-state", "RESTRICTED", "warn");
    setBadge("#product-badge", "product: restricted", "muted");
  }

  if (capabilities) {
    setMetric("#tool-count", capabilities.tool_count, "ok");
    setBadge("#capability-badge", `MCP: ${capabilities.tool_count} tools`, "safe");
    $("#capability-detail").textContent = pretty({
      surface: capabilities.surface,
      mode: capabilities.mode,
      capability_contract: capabilities.capability_contract,
      error_contract: capabilities.error_contract,
      tool_groups: capabilities.tool_groups,
    });
  } else {
    setMetric("#tool-count", "—", "warn");
    setBadge("#capability-badge", "MCP: restricted", "muted");
    $("#capability-detail").textContent = "Capability introspection is unavailable under the active product/profile boundary.";
  }

  const authority = health?.authority;
  if (authorityClosed(authority)) {
    setBadge("#authority-badge", "authority: fail-closed", "lock");
  } else {
    setBadge("#authority-badge", "authority: inspect", "muted");
  }

  const note = $("#system-note");
  if (health?.status === "READY") {
    note.textContent = "Local Workspace gate is open. Prototype execution remains bounded by the signed product entitlement and customer profile.";
  } else if (health?.reason) {
    note.textContent = `Workspace blocked: ${health.reason}`;
  } else {
    note.textContent = "Workspace health could not be verified.";
  }
}

function renderBestiary(payload) {
  const grid = $("#bestiary-grid");
  const state = $("#bestiary-state");
  grid.replaceChildren();

  const species = Array.isArray(payload?.species) ? payload.species : [];
  if (!species.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "Bestiary introspection is unavailable under the active product/profile boundary.";
    grid.appendChild(empty);
    state.className = "mini-state fail";
    state.textContent = "restricted";
    setMetric("#species-count", "—", "warn");
    return;
  }

  species.forEach((item) => {
    const card = document.createElement("div");
    card.className = "beast-card";
    card.title = `${text(item.name)} — ${text(item.role)}`;

    const name = document.createElement("div");
    name.className = "beast-name";
    name.textContent = text(item.name);

    const stage = document.createElement("div");
    stage.className = "beast-stage";
    stage.textContent = text(item.stage);

    const role = document.createElement("div");
    role.className = "beast-role";
    role.textContent = text(item.role);

    card.append(name, stage, role);
    grid.appendChild(card);
  });

  const topology = Array.isArray(payload.topology) ? payload.topology.join(" → ") : "topology available";
  state.className = "mini-state ok";
  state.textContent = `${species.length} roles`;
  state.title = topology;
  setMetric("#species-count", species.length, "ok");
}

async function loadCockpit() {
  sessionState.health = null;
  sessionState.product = null;
  sessionState.capabilities = null;
  sessionState.bestiary = null;
  setMetric("#workspace-state", "CHECKING");
  setMetric("#product-state", "CHECKING");
  setMetric("#tool-count", "—");
  setMetric("#species-count", "—");

  const healthResult = await Promise.allSettled([
    fetchJson("/api/health"),
    fetchJson("/api/status"),
    fetchJson("/api/bestiary"),
  ]);

  if (healthResult[0].status === "fulfilled") {
    sessionState.health = healthResult[0].value;
    recordActivity(
      healthResult[0].value.status === "READY" ? "pass" : "fail",
      `Workspace health: ${healthResult[0].value.status}`,
    );
  } else {
    recordActivity("fail", `Workspace health unavailable: ${healthResult[0].reason.message || healthResult[0].reason}`);
  }

  if (healthResult[1].status === "fulfilled") {
    sessionState.product = healthResult[1].value.product || null;
    sessionState.capabilities = healthResult[1].value.capabilities || null;
  } else {
    recordActivity("info", `Status introspection restricted: ${healthResult[1].reason.message || healthResult[1].reason}`);
  }

  if (healthResult[2].status === "fulfilled") {
    sessionState.bestiary = healthResult[2].value;
    renderBestiary(sessionState.bestiary);
    recordActivity("info", `Bestiary loaded: ${sessionState.bestiary.species_count || 0} roles`);
  } else {
    renderBestiary(null);
    recordActivity("info", `Bestiary introspection restricted: ${healthResult[2].reason.message || healthResult[2].reason}`);
  }

  renderSystemCockpit();
}

async function refreshCockpit() {
  if (refreshCockpitButton.disabled) return;
  refreshCockpitButton.disabled = true;
  const originalLabel = refreshCockpitButton.textContent;
  refreshCockpitButton.textContent = "Refreshing…";
  try {
    await loadCockpit();
    recordActivity("info", "Cockpit state refreshed.");
  } finally {
    refreshCockpitButton.disabled = false;
    refreshCockpitButton.textContent = originalLabel || "Refresh";
  }
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
    recordActivity("info", "Reference candidate loaded.");
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

function svgText(parent, x, y, value, className, anchor = "start") {
  const node = svgElement("text", { x, y, class: className, "text-anchor": anchor });
  node.textContent = value;
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

function truncate(value, max = 24) {
  const rendered = String(value || "");
  return rendered.length > max ? `${rendered.slice(0, max - 1)}…` : rendered;
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
    const coefficients = Array.isArray(term.ell) ? term.ell : [];
    const activeLanes = coefficients
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
      svg.appendChild(svgElement("line", {
        x1: 190,
        y1: laneY,
        x2: operatorX,
        y2: centerY,
        class: "graph-edge accent",
      }));
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

    svg.appendChild(svgElement("line", {
      x1: operatorX + operatorW,
      y1: centerY,
      x2: sourceX,
      y2: centerY,
      class: "graph-edge",
    }));

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
  $("#audit-view").textContent =
    "The candidate or request failed before a validated prototype receipt was produced.";
  $("#test-grid").replaceChildren();
  $("#test-detail").textContent = userAction || message;
  $("#receipt-view").textContent = contract ? pretty(contract) : "No machine-readable error receipt produced.";

  const stateMessage = contract?.error_code
    ? `${contract.error_code}: ${userAction || message}`
    : message;
  setRunState("fail", stateMessage);
}

async function runCandidate() {
  if (runButton.disabled) return;
  clearErrorGuidance();
  runButton.disabled = true;
  retryErrorButton.disabled = true;
  markCandidate(true);
  setRunState("running", "compiling → prototyping → testing…");
  let candidate = null;
  try {
    candidate = parseCandidate();
    const request = buildRequest(candidate);
    const payload = await fetchJson("/api/prototype", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    renderResponse(payload, candidate);

    const status = payload?.response?.status || "UNKNOWN";
    const id = candidate.candidate_id || "unnamed candidate";
    const note = problemBrief.value.trim();
    recordActivity(
      status === "VALIDATED_PROTOTYPE" ? "pass" : "fail",
      `${id}: ${status}${note ? ` — ${truncate(note, 70)}` : ""}`,
    );
  } catch (error) {
    markCandidate(false);
    renderError(error);
    const contract = error instanceof WorkspaceHttpError ? error.contract : null;
    recordActivity(
      "fail",
      `${candidate?.candidate_id || "candidate"}: ${contract?.error_code || error.message || error}${contract?.user_action ? ` — ${contract.user_action}` : ""}`,
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
refreshCockpitButton.addEventListener("click", refreshCockpit);
retryErrorButton.addEventListener("click", runCandidate);

document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && !runButton.disabled) {
    event.preventDefault();
    runCandidate();
  }
});

clearActivityButton.addEventListener("click", () => {
  sessionState.activity = [];
  renderActivity();
});

$$(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    $$(".tab").forEach((node) => node.classList.remove("active"));
    $$(".tab-panel").forEach((node) => node.classList.remove("active"));
    button.classList.add("active");
    $(`#tab-${button.dataset.tab}`).classList.add("active");
  });
});

setTechnicalMode(readTechnicalModePreference(), { persist: false });
renderActivity();
Promise.allSettled([loadCockpit(), loadExample()]).then(() => {
  if (footerMessage.textContent === "Ready.") {
    footerMessage.textContent = "Workspace ready.";
  }
});
