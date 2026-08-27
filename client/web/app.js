"use strict";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const SVG_NS = "http://www.w3.org/2000/svg";

const candidateEditor = $("#candidate-editor");
const problemBrief = $("#problem-brief");
const sampleCount = $("#sample-count");
const runButton = $("#run-candidate");
const loadButton = $("#load-example");
const runStatus = $("#run-status");
const verdict = $("#verdict");
const inputState = $("#input-state");
const footerMessage = $("#footer-message");

function pretty(value) {
  return JSON.stringify(value, null, 2);
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
    const response = await fetch("/api/example", { cache: "no-store" });
    if (!response.ok) throw new Error(`Example request failed: HTTP ${response.status}`);
    const request = await response.json();
    candidateEditor.value = pretty(request.candidate);
    sampleCount.value = request.sample_count || 64;
    if (!problemBrief.value.trim()) {
      problemBrief.value = "Inspect the supplied phase-native relations, compile their invariant structure into PhaseNav character IR, build a reference prototype and attempt to falsify its numerical conformance.";
    }
    markCandidate(true);
    setRunState("", "example loaded");
  } catch (error) {
    markCandidate(false);
    setRunState("fail", String(error.message || error));
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

    const tau = term.tau_f64_hex ? Number.parseFloat(Number.parseFloat(0).toString()) : 0;
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
  $("#prototype-source").textContent = String(error.message || error);
  $("#audit-view").textContent = "The candidate or request failed before a validated prototype receipt was produced.";
  $("#test-grid").replaceChildren();
  $("#test-detail").textContent = String(error.message || error);
  $("#receipt-view").textContent = "No receipt produced.";
  setRunState("fail", String(error.message || error));
}

async function runCandidate() {
  runButton.disabled = true;
  markCandidate(true);
  setRunState("running", "compiling → prototyping → testing…");
  try {
    const candidate = parseCandidate();
    const request = buildRequest(candidate);
    const response = await fetch("/api/prototype", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    renderResponse(payload, candidate);
  } catch (error) {
    markCandidate(false);
    renderError(error);
  } finally {
    runButton.disabled = false;
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

$$(".tab").forEach((button) => {
  button.addEventListener("click", () => {
    $$(".tab").forEach((node) => node.classList.remove("active"));
    $$(".tab-panel").forEach((node) => node.classList.remove("active"));
    button.classList.add("active");
    $(`#tab-${button.dataset.tab}`).classList.add("active");
  });
});

loadExample();
