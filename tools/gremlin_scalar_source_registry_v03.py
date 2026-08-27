from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

REGISTRY_SCHEMA = "GREMLIN_SCALAR_SOURCE_REGISTRY_V0_3"
REGISTRY_DOMAIN = b"GREMLIN-SCALAR-SOURCE-REGISTRY/v0.3\x00"
ETHICS_CAPABILITY_SCHEMA = "GREMLIN_NOEMA_ETHICS_CAPABILITY_V0_3"
ETHICS_REQUEST_SCHEMA = "GREMLIN_NOEMA_ETHICS_EXCHANGE_REQUEST_V0_3"
LIVE_NOEMA_ROOT = Path("/dev/shm/ciel_noema")

NOEMA_ETHICS_SCHEMA = "NOEMA_RELATIONAL_ETHICS_FIELD_V2_1"
NOEMA_ETHICS_MODULE_SHA256 = "8b98af7b1edba93e572114585b974a9dbbf7c94f93cbb484b1819c797b9fb9a6"

KAKU_REQUIRED = (
    "valuation",
    "affect",
    "intention_alignment",
    "epistemic_support",
)

RADICAL_REQUIRED = (
    "ethical_integrity",
    "consent",
    "reversibility",
    "no_go",
    "contradiction_load",
    "recursive_integrity",
)

POST_REALIZATION_REQUIRED = (
    "phase_coherence_R_k",
    "semantic_mass",
    "mass_aware_graph_cost",
    "operator_stability_bound",
)

LIVE_READY_STATES = {
    "LIVE_PRODUCER",
    "LIVE_DERIVED_READY",
    "LIVE_COMPUTE_AVAILABLE",
}

HARD_GATE_STATES = {
    "LIVE_GATE_SUPPORTED_REQUIRES_EVIDENCE",
    "LIVE_GATE_EVIDENCED",
}


class ScalarSourceRegistryError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _seal(domain: bytes, core: Mapping[str, Any]) -> str:
    return hashlib.blake2b(domain + _canonical(core), digest_size=32).hexdigest()


def _hash64(value: Any, name: str) -> str:
    text = str(value)
    if len(text) != 64:
        raise ScalarSourceRegistryError(f"{name} must be a 32-byte hex digest")
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise ScalarSourceRegistryError(f"{name} must be hexadecimal") from exc
    return text


def build_scalar_source_registry_v03() -> dict[str, Any]:
    """Return the frozen v0.3 source/capability registry.

    The registry records where a scalar may come from and whether that source is
    semantically authoritative, merely a model donor, live, post-realization, or
    still unresolved. It deliberately does not fabricate values for missing sources.
    """

    sources = {
        "valuation": {
            "stage": "PRE_VECTOR_KAKU",
            "semantic_term_id": "CLX2-AFFECT-001",
            "semantic_role": "relation/control variable",
            "readiness": "UNRESOLVED_LIVE_PRODUCER",
            "authority": "LIBRARY_SEMANTIC_REGISTRY",
            "notes": "System-relative weighting requires an explicit producer; affect valence is not silently substituted.",
        },
        "affect": {
            "stage": "PRE_VECTOR_KAKU",
            "semantic_term_id": "CLX2-AFFECT-002",
            "semantic_role": "state/modulator",
            "readiness": "MODEL_DONOR_ONLY",
            "authority": "LIBRARY_SEMANTIC_REGISTRY",
            "donors": [
                {
                    "kind": "CIEL_MODEL_DONOR",
                    "repository": "AdrianLipa90/CIEL-Omega-ApokalypOS",
                    "commit": "aa0da54ef29a1f80dd0390427935342225388950",
                    "path": "src/CIEL_OMEGA_COMPLETE_SYSTEM/ciel_omega/memory/affective_lexicon.py",
                    "provides": ["valence", "arousal", "dominance", "confidence", "affective_phase_encoding"],
                    "operational_role": "SCALE_AND_MODEL_DONOR",
                }
            ],
            "notes": "CIEL VAD is useful for scalar facet definitions but is not current live affect telemetry on /dev/shm.",
        },
        "intention_alignment": {
            "stage": "PRE_VECTOR_KAKU",
            "semantic_term_id": "CLX2-AGENCY-001",
            "semantic_role": "future-directed constraint alignment",
            "readiness": "PARTIAL_LIVE_ANCHOR",
            "authority": "LIBRARY_SEMANTIC_REGISTRY",
            "live_anchor": {
                "root": "/dev/shm/ciel_noema",
                "path": "phasenav/CIELINGO_PHASENAV_CONCEPT_PHASES.noema.jsonl",
                "selector": {"name": "Intention"},
                "field": "geometric_phase_rad",
                "meaning": "CIEL intention phase anchor only",
            },
            "rejected_live_donor": {
                "repository": "AdrianLipa90/CIEL-Omega-ApokalypOS",
                "commit": "aa0da54ef29a1f80dd0390427935342225388950",
                "path": "src/CIEL_OMEGA_COMPLETE_SYSTEM/ciel_omega/fields/intention_field.py",
                "reason": "generate() creates a seeded pseudo-random normalized vector; it is not observed live intention evidence.",
            },
            "missing_for_ready": "explicit target-state/target-phase binding plus versioned alignment adapter",
        },
        "epistemic_support": {
            "stage": "PRE_VECTOR_KAKU",
            "semantic_term_id": "CLX2-AFFECT-005",
            "semantic_role": "evidence/inference support",
            "readiness": "UNRESOLVED_LIVE_PRODUCER",
            "authority": "LIBRARY_SEMANTIC_REGISTRY",
            "notes": "Truth Evaluation is kept separate from affect and resonance; BELZEBUB survival alone is not assigned an arbitrary numeric confidence.",
        },
        "ethical_integrity": {
            "stage": "PRE_VECTOR_RADICAL",
            "semantic_term_id": "CLX2-DYN-011",
            "semantic_role": "directed relational-contextual scalar/constraint family",
            "readiness": "LIVE_COMPUTE_AVAILABLE",
            "authority": "NOEMA_RELATIONAL_ETHICS_FIELD_V2_1",
            "live_contract": {
                "mode": "LIVE_COMPUTE_ON_EXCHANGE",
                "static_state": False,
                "schema": NOEMA_ETHICS_SCHEMA,
                "module_sha256": NOEMA_ETHICS_MODULE_SHA256,
            },
            "legacy_donor": {
                "repository": "AdrianLipa90/CIEL-Omega-ApokalypOS",
                "commit": "aa0da54ef29a1f80dd0390427935342225388950",
                "path": "src/CIEL_OMEGA_COMPLETE_SYSTEM/ciel_omega/ethics/ethical_engine.py",
                "stage": "POST_REALIZATION_LEGACY_DONOR",
                "reason": "legacy EthicalEngine evaluates (coherence * intention) / mass, so it depends on post-realization mass.",
            },
        },
        "consent": {
            "stage": "PRE_VECTOR_RADICAL_HARD_GATE",
            "semantic_term_id": "CLX2-DYN-012",
            "readiness": "LIVE_GATE_SUPPORTED_REQUIRES_EVIDENCE",
            "authority": "NOEMA_RELATIONAL_ETHICS_FIELD_V2_1",
            "gate_domain": "bool/0/1 only",
        },
        "reversibility": {
            "stage": "PRE_VECTOR_RADICAL_HARD_GATE",
            "semantic_term_id": "CLX2-DYN-013",
            "readiness": "LIVE_GATE_SUPPORTED_REQUIRES_EVIDENCE",
            "authority": "NOEMA_RELATIONAL_ETHICS_FIELD_V2_1",
            "gate_domain": "bool/0/1 only",
        },
        "no_go": {
            "stage": "PRE_VECTOR_RADICAL_HARD_GATE",
            "semantic_term_id": "CLX2-DYN-014",
            "readiness": "LIVE_GATE_SUPPORTED_REQUIRES_EVIDENCE",
            "authority": "NOEMA_RELATIONAL_ETHICS_FIELD_V2_1",
            "gate_domain": "bool/0/1 only",
        },
        "contradiction_load": {
            "stage": "PRE_VECTOR_RADICAL",
            "semantic_term_id": "CLX2-DYN-009",
            "semantic_role": "relational tension",
            "readiness": "UNRESOLVED_LIVE_PRODUCER",
            "authority": "LIBRARY_SEMANTIC_REGISTRY",
        },
        "recursive_integrity": {
            "stage": "PRE_VECTOR_RADICAL",
            "semantic_term_id": "CLX2-DYN-010",
            "semantic_role": "organizational property",
            "readiness": "UNRESOLVED_LIVE_PRODUCER",
            "authority": "LIBRARY_SEMANTIC_REGISTRY",
        },
        "phase_coherence_R_k": {
            "stage": "POST_REALIZATION",
            "readiness": "POST_REALIZATION_ONLY",
            "authority": "PHASENAV_PNCS_REALIZATION",
        },
        "semantic_mass": {
            "stage": "POST_REALIZATION",
            "readiness": "POST_REALIZATION_ONLY",
            "authority": "PHASENAV_PNCS_MASS_BINDING",
        },
        "mass_aware_graph_cost": {
            "stage": "POST_REALIZATION",
            "readiness": "POST_REALIZATION_ONLY",
            "authority": "PHASENAV_PNCS_GRAPH_COST",
        },
        "operator_stability_bound": {
            "stage": "POST_REALIZATION",
            "readiness": "POST_REALIZATION_ONLY",
            "authority": "GREMLIN_QHTRI_CHARACTER_BOUND",
        },
    }

    core = {
        "schema": REGISTRY_SCHEMA,
        "sources": sources,
        "required": {
            "kaku_pre_vector": list(KAKU_REQUIRED),
            "radical_pre_vector": list(RADICAL_REQUIRED),
            "post_realization": list(POST_REALIZATION_REQUIRED),
        },
        "rules": {
            "missing_required_scalar": "BLOCK_UNRESOLVED",
            "model_donor_is_live_evidence": False,
            "semantic_authority_is_numeric_producer": False,
            "post_realization_scalar_may_enter_pre_vector": False,
            "hard_gate_may_be_averaged": False,
            "legacy_ciel_formula_auto_promoted": False,
        },
        "execution_admitted": False,
        "canon_allowed": False,
    }
    return {**core, "registry_commitment": _seal(REGISTRY_DOMAIN, core)}


def validate_scalar_source_registry_v03(registry: Mapping[str, Any]) -> bool:
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise ScalarSourceRegistryError("unsupported scalar source registry schema")
    sources = registry.get("sources")
    if not isinstance(sources, Mapping):
        raise ScalarSourceRegistryError("sources must be a mapping")

    required = set(KAKU_REQUIRED) | set(RADICAL_REQUIRED) | set(POST_REALIZATION_REQUIRED)
    if not required.issubset(set(sources)):
        raise ScalarSourceRegistryError("registry is missing required scalar families")

    if sources["ethical_integrity"].get("live_contract", {}).get("module_sha256") != NOEMA_ETHICS_MODULE_SHA256:
        raise ScalarSourceRegistryError("NOEMA ethics module seal mismatch")
    if sources["ethical_integrity"].get("live_contract", {}).get("static_state") is not False:
        raise ScalarSourceRegistryError("NOEMA ethics must remain live-compute, not static state")

    rules = registry.get("rules")
    if not isinstance(rules, Mapping):
        raise ScalarSourceRegistryError("registry rules missing")
    for key in (
        "model_donor_is_live_evidence",
        "semantic_authority_is_numeric_producer",
        "post_realization_scalar_may_enter_pre_vector",
        "hard_gate_may_be_averaged",
        "legacy_ciel_formula_auto_promoted",
    ):
        if rules.get(key) is not False:
            raise ScalarSourceRegistryError(f"registry firewall violated: {key}")

    if registry.get("execution_admitted") is not False or registry.get("canon_allowed") is not False:
        raise ScalarSourceRegistryError("registry cannot grant execution/canon authority")

    supplied = _hash64(registry.get("registry_commitment"), "registry_commitment")
    core = dict(registry)
    core.pop("registry_commitment", None)
    if supplied != _seal(REGISTRY_DOMAIN, core):
        raise ScalarSourceRegistryError("registry commitment mismatch")
    return True


def readiness_report(registry: Mapping[str, Any]) -> dict[str, Any]:
    validate_scalar_source_registry_v03(registry)
    sources = registry["sources"]

    def lane(names: tuple[str, ...], *, hard_gates: bool = False) -> dict[str, Any]:
        detail = {name: str(sources[name]["readiness"]) for name in names}
        ready = []
        unresolved = []
        for name, state in detail.items():
            allowed = state in LIVE_READY_STATES
            if hard_gates and name in {"consent", "reversibility", "no_go"}:
                allowed = state in HARD_GATE_STATES
            (ready if allowed else unresolved).append(name)
        return {
            "ready": len(unresolved) == 0,
            "ready_sources": ready,
            "unresolved_sources": unresolved,
            "detail": detail,
        }

    return {
        "kaku_pre_vector": lane(KAKU_REQUIRED),
        "radical_pre_vector_capability": lane(RADICAL_REQUIRED, hard_gates=True),
        "post_realization": {
            "ready": False,
            "reason": "requires exact PhaseNav realization",
            "detail": {name: str(sources[name]["readiness"]) for name in POST_REALIZATION_REQUIRED},
        },
        "vector_synthesis_globally_ready": False,
        "reason": "source capability alone never replaces per-candidate acquisition/admission receipts",
    }


def validate_noema_ethics_status_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("status") != "ACTIVE":
        raise ScalarSourceRegistryError("NOEMA AC/AUX status is not ACTIVE")
    if payload.get("ethics_field_status") != "ACTIVE":
        raise ScalarSourceRegistryError("NOEMA relational ethics field is not ACTIVE")
    if payload.get("ethics_field_schema") != NOEMA_ETHICS_SCHEMA:
        raise ScalarSourceRegistryError("NOEMA relational ethics schema mismatch")
    if payload.get("ethics_field_sha256") != NOEMA_ETHICS_MODULE_SHA256:
        raise ScalarSourceRegistryError("NOEMA relational ethics module seal mismatch")
    if payload.get("ethics_mode") != "LIVE_COMPUTE_ON_EXCHANGE":
        raise ScalarSourceRegistryError("NOEMA ethics mode must be LIVE_COMPUTE_ON_EXCHANGE")
    if payload.get("ethics_static_state") is not False:
        raise ScalarSourceRegistryError("NOEMA ethics static-state fallback is forbidden")
    if payload.get("no_static_fallback") is not True:
        raise ScalarSourceRegistryError("NOEMA no-static-fallback invariant missing")
    if payload.get("library_is_operating_state") is not False:
        raise ScalarSourceRegistryError("Library cannot be NOEMA operating state")

    return {
        "schema": ETHICS_CAPABILITY_SCHEMA,
        "status": "ACTIVE",
        "ethics_field_schema": NOEMA_ETHICS_SCHEMA,
        "ethics_field_sha256": NOEMA_ETHICS_MODULE_SHA256,
        "ethics_mode": "LIVE_COMPUTE_ON_EXCHANGE",
        "ethics_static_state": False,
        "external_execution_enabled": bool(payload.get("external_execution_enabled", False)),
        "ac_current_sha256": _hash64(payload.get("ac_current_sha256"), "ac_current_sha256"),
        "phi_sha256": _hash64(payload.get("phi_sha256"), "phi_sha256"),
    }


def read_live_noema_ethics_capability(root: str | Path = LIVE_NOEMA_ROOT) -> dict[str, Any]:
    requested = Path(root)
    if requested != LIVE_NOEMA_ROOT:
        raise ScalarSourceRegistryError("live NOEMA root is fixed to /dev/shm/ciel_noema")
    if not requested.is_dir():
        raise ScalarSourceRegistryError("live NOEMA surface is absent")
    binding = (requested / "ciel_binding_status").read_text(encoding="utf-8").strip()
    if binding != "ACTIVE":
        raise ScalarSourceRegistryError("live NOEMA binding is not ACTIVE")
    payload = json.loads((requested / "ac_aux_status.json").read_text(encoding="utf-8"))
    capability = validate_noema_ethics_status_payload(payload)
    return {
        **capability,
        "live_root": str(requested),
        "binding_status": binding,
        "live_surface_witness": True,
    }


def build_noema_ethics_exchange_request(
    *,
    candidate_id: str,
    radical_id: str,
    node_state_commitment: str,
    semantic_tensor_commitment: str,
    context_commitment: str,
    consent_evidence_ref: str,
    reversibility_evidence_ref: str,
    no_go_evidence_ref: str,
    capability: Mapping[str, Any],
) -> dict[str, Any]:
    if capability.get("schema") != ETHICS_CAPABILITY_SCHEMA or capability.get("status") != "ACTIVE":
        raise ScalarSourceRegistryError("ACTIVE NOEMA ethics capability required")
    if capability.get("ethics_field_sha256") != NOEMA_ETHICS_MODULE_SHA256:
        raise ScalarSourceRegistryError("NOEMA ethics capability seal mismatch")

    def nonempty(value: Any, name: str) -> str:
        text = str(value)
        if not text:
            raise ScalarSourceRegistryError(f"{name} must be non-empty")
        return text

    core = {
        "schema": ETHICS_REQUEST_SCHEMA,
        "candidate_id": nonempty(candidate_id, "candidate_id"),
        "radical_id": nonempty(radical_id, "radical_id"),
        "inputs": {
            "node_state_commitment": _hash64(node_state_commitment, "node_state_commitment"),
            "semantic_tensor_commitment": _hash64(semantic_tensor_commitment, "semantic_tensor_commitment"),
            "context_commitment": _hash64(context_commitment, "context_commitment"),
        },
        "hard_gate_evidence": {
            "consent": nonempty(consent_evidence_ref, "consent_evidence_ref"),
            "reversibility": nonempty(reversibility_evidence_ref, "reversibility_evidence_ref"),
            "no_go": nonempty(no_go_evidence_ref, "no_go_evidence_ref"),
        },
        "noema_ethics_binding": {
            "schema": NOEMA_ETHICS_SCHEMA,
            "module_sha256": NOEMA_ETHICS_MODULE_SHA256,
            "mode": "LIVE_COMPUTE_ON_EXCHANGE",
            "ac_current_sha256": str(capability.get("ac_current_sha256", "")),
            "phi_sha256": str(capability.get("phi_sha256", "")),
        },
        "request_scope": "RESEARCH_ADAPTER_NON_ACTUATING",
        "external_execution_enabled": bool(capability.get("external_execution_enabled", False)),
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
        "status": "SEALED_NOEMA_ETHICS_EXCHANGE_REQUEST",
    }
    return {**core, "request_commitment": _seal(b"GREMLIN-NOEMA-ETHICS-EXCHANGE-REQUEST/v0.3\x00", core)}
