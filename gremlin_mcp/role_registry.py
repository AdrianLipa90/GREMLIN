from __future__ import annotations

BESTIARY_ROLES: dict[str, dict[str, str]] = {
    "HUMMINGBIRD": {"stage": "capture", "role": "fast append-only capture"},
    "OCTOPUS": {"stage": "routing", "role": "auditable semantic route mask and bounded fanout"},
    "SPIDER": {"stage": "specialist", "role": "relation, dependency and isomorphism scan"},
    "RAVEN": {"stage": "specialist", "role": "memory and similarity scan"},
    "HOUND": {"stage": "specialist", "role": "contradiction, anomaly and test-target scan"},
    "MOLE": {"stage": "specialist", "role": "deep local derivation"},
    "OWL": {"stage": "specialist", "role": "epistemic audit"},
    "ANT": {"stage": "specialist", "role": "bounded combinatorial scan"},
    "MANTIS": {"stage": "specialist", "role": "duplicate and dead-branch pruning"},
    "FOX": {"stage": "specialist", "role": "strategic planning and decomposition"},
    "BEAVER": {"stage": "specialist", "role": "candidate construction and prototyping"},
    "BAT": {"stage": "specialist", "role": "weak-signal, harmonic and phase-pattern detection"},
    "CANARY": {"stage": "sentinel", "role": "runtime drift and early-warning sentinel"},
    "SERPENT": {"stage": "sensor", "role": "latent-field temperature, taste and novelty sensing"},
    "CHAMELEON": {"stage": "transform", "role": "reversible representation/profile transformation"},
    "ELEPHANT": {"stage": "memory", "role": "append-only relational memory consolidation, replay and retention planning"},
    "BEES": {"stage": "coherence", "role": "local overlap coherence, anti-entropy delta and reconciliation proposals"},
    "BELZEBUB": {"stage": "synthesis", "role": "defensive candidate synthesis"},
    "FERRET": {"stage": "actuation", "role": "explicitly authorized interactive web actuator"},
    "GREMLIN": {"stage": "aggregate", "role": "aggregate verified heads and emit research candidates"},
}

BESTIARY_ROLE_NAMES = frozenset(BESTIARY_ROLES)

# These roles are architectural boundaries, not ordinary exact-cover workers.
CORE_BOUNDARY_SPECIES = frozenset({"HUMMINGBIRD", "OCTOPUS", "GREMLIN", "FERRET"})

# These roles are legitimate execution modules but do not yet have validated
# external PhaseNav worker carriers. They require explicit local adapters.
LOCAL_EXECUTION_SPECIES = frozenset({"ELEPHANT", "BEES"})

ROUTABLE_EXECUTION_SPECIES = (
    BESTIARY_ROLE_NAMES - CORE_BOUNDARY_SPECIES
)

if not LOCAL_EXECUTION_SPECIES <= ROUTABLE_EXECUTION_SPECIES:
    raise RuntimeError("local execution species must be routable execution species")

__all__ = [
    "BESTIARY_ROLES",
    "BESTIARY_ROLE_NAMES",
    "CORE_BOUNDARY_SPECIES",
    "LOCAL_EXECUTION_SPECIES",
    "ROUTABLE_EXECUTION_SPECIES",
]
