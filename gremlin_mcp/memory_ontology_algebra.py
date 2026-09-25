from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import cmath
import hashlib
import json
import math
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "GREMLIN_MEMORY_ONTOLOGY_ALGEBRA_V0_1"
VERSION = "0.1.0"

SOURCE_REPOSITORY = "AdrianLipa90/Memory-Ontology"
SOURCE_MAIN_COMMIT = "c0973d26cc64c0d9018b67707e5708e084017ad8"
SOURCE_BLOBS = {
    "memory_representation_category_v04": "099a19fb3418c9b6415ef332e87ec38c5d5bee2e",
    "behavioral_core_v04": "fca0fc613be268bd085bc37892242f269529fba2e",
    "prime_hilbert_collatz_association": "6c517c04ab1518c2bc746222ed2a00d7113e7c12",
    "orbital_ternary_memory_algebra": "421db4ca0ab5b7ca6c876c5744552969caef5a81",
    "final_receipt": "7402cc9c3ce8c5d2ba61942f709fb2c26f8e4e77",
}
SOURCE_RECEIPT_STATUS = "TARGETED_LOCAL_PASS_READY_FOR_MAIN"
SOURCE_RECEIPT_GATE = {"passed": 63, "failed": 0, "elapsed_s": 0.71}

TRITS = (-1, 0, 1)
TAU = math.tau

MEMORY_ONTOLOGY_ROLE_BINDINGS: dict[str, str] = {
    "SPIDER": "representation graph / exact relation and isomorphism structure",
    "RAVEN": "historical lineage / prior representation retrieval",
    "HOUND": "contradiction, inverse-witness and domain/image falsification",
    "MOLE": "algebraic composition, dissociation and local derivation",
    "OWL": "epistemic/claim-boundary audit",
    "MANTIS": "duplicate, dead-branch and redundant representation pruning",
    "CHAMELEON": "typed representation transformation candidate",
    "ELEPHANT": "append-only historical consolidation and replay",
    "BEES": "cross-representation coherence and anti-entropy",
    "BELZEBUB": "defensive bounded synthesis over admitted candidates",
    "GREMLIN": "aggregate witnessed heads without canon promotion",
}


class MemoryOntologyAlgebraError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MemoryOntologyAlgebraError(
            "value must be finite canonical JSON"
        ) from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MemoryOntologyAlgebraError(
            f"{field} must be a non-empty string"
        )
    return value.strip()


def _positive_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise MemoryOntologyAlgebraError(
            f"{field} must be a positive integer"
        )
    return value


def _error_fraction(value: Any) -> Fraction:
    if isinstance(value, bool):
        raise MemoryOntologyAlgebraError("error bound cannot be boolean")
    if isinstance(value, Fraction):
        out = value
    elif isinstance(value, int):
        out = Fraction(value, 1)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise MemoryOntologyAlgebraError(
                "error bound must be finite"
            )
        out = Fraction(str(value))
    elif isinstance(value, str):
        try:
            out = Fraction(value)
        except Exception as exc:
            raise MemoryOntologyAlgebraError(
                "invalid rational error bound"
            ) from exc
    else:
        raise MemoryOntologyAlgebraError(
            "unsupported error bound type"
        )
    if out < 0:
        raise MemoryOntologyAlgebraError(
            "error bound must be non-negative"
        )
    return out


# ---------------------------------------------------------------------------
# Prime/Hilbert ordered history
# ---------------------------------------------------------------------------

def primes_first(count: int) -> tuple[int, ...]:
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise MemoryOntologyAlgebraError(
            "count must be a non-negative integer"
        )
    out: list[int] = []
    n = 2
    while len(out) < count:
        prime = True
        limit = math.isqrt(n)
        for p in out:
            if p > limit:
                break
            if n % p == 0:
                prime = False
                break
        if prime:
            out.append(n)
        n += 1 if n == 2 else 2
    return tuple(out)


def encode_prime_word(symbols: Iterable[int]) -> int:
    word = tuple(symbols)
    code = 1
    for p, exponent in zip(primes_first(len(word)), word):
        _positive_int(exponent, "prime-word symbol")
        code *= p**exponent
    return code


def decode_prime_word(code: int) -> tuple[int, ...]:
    _positive_int(code, "prime-word code")
    if code == 1:
        return ()
    remainder = code
    out: list[int] = []
    index = 0
    while remainder > 1:
        p = primes_first(index + 1)[-1]
        if remainder % p:
            raise MemoryOntologyAlgebraError(
                "prime-word code must have consecutive prime support"
            )
        exponent = 0
        while remainder % p == 0:
            remainder //= p
            exponent += 1
        out.append(exponent)
        index += 1
    return tuple(out)


def prime_position_shift(code: int, offset: int) -> int:
    _positive_int(code, "prime-word code")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise MemoryOntologyAlgebraError(
            "offset must be a non-negative integer"
        )
    word = decode_prime_word(code)
    if not word:
        return 1
    ps = primes_first(offset + len(word))
    out = 1
    for j, exponent in enumerate(word):
        out *= ps[offset + j] ** exponent
    return out


def associate_prime_codes(left_code: int, right_code: int) -> int:
    left = decode_prime_word(left_code)
    right = decode_prime_word(right_code)
    direct = encode_prime_word(left + right)
    shifted = left_code * prime_position_shift(
        right_code, len(left)
    )
    if direct != shifted:
        raise AssertionError(
            "prime/Hilbert association identity failed"
        )
    return direct


def dissociate_prime_code(
    code: int,
    cut: int,
) -> tuple[int, int]:
    word = decode_prime_word(code)
    if (
        isinstance(cut, bool)
        or not isinstance(cut, int)
        or not 0 <= cut <= len(word)
    ):
        raise MemoryOntologyAlgebraError(
            "cut must lie in [0, word_length]"
        )
    return (
        encode_prime_word(word[:cut]),
        encode_prime_word(word[cut:]),
    )


# ---------------------------------------------------------------------------
# Historical category -> behavioral quotient
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HistoryStep:
    """One validated historical edge.

    Equal symbols never imply invertibility. Cancellation requires explicit
    reciprocal edge ids and exact endpoint reversal.
    """

    edge_id: str
    source_id: str
    target_id: str
    symbol_code: int
    inverse_edge_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "edge_id", _nonempty(self.edge_id, "edge_id")
        )
        object.__setattr__(
            self, "source_id", _nonempty(self.source_id, "source_id")
        )
        object.__setattr__(
            self, "target_id", _nonempty(self.target_id, "target_id")
        )
        _positive_int(self.symbol_code, "symbol_code")
        if self.inverse_edge_id is not None:
            object.__setattr__(
                self,
                "inverse_edge_id",
                _nonempty(
                    self.inverse_edge_id,
                    "inverse_edge_id",
                ),
            )

    def is_exact_inverse_of(
        self,
        previous: "HistoryStep",
    ) -> bool:
        return (
            previous.inverse_edge_id == self.edge_id
            and self.inverse_edge_id == previous.edge_id
            and previous.source_id == self.target_id
            and previous.target_id == self.source_id
        )


@dataclass(frozen=True)
class HistoricalTrace:
    subject_id: str
    steps: tuple[HistoryStep, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "subject_id",
            _nonempty(self.subject_id, "subject_id"),
        )
        steps = tuple(self.steps)
        current: str | None = None
        for step in steps:
            if not isinstance(step, HistoryStep):
                raise MemoryOntologyAlgebraError(
                    "steps must contain HistoryStep"
                )
            if current is not None and step.source_id != current:
                raise MemoryOntologyAlgebraError(
                    "historical trace endpoints do not compose"
                )
            current = step.target_id
        object.__setattr__(self, "steps", steps)

    @property
    def prime_lineage_code(self) -> int:
        return encode_prime_word(
            step.symbol_code for step in self.steps
        )

    def historical_signature(self) -> dict[str, Any]:
        body = {
            "subject_id": self.subject_id,
            "steps": [
                {
                    "edge_id": step.edge_id,
                    "source_id": step.source_id,
                    "target_id": step.target_id,
                    "symbol_code": step.symbol_code,
                    "inverse_edge_id": step.inverse_edge_id,
                }
                for step in self.steps
            ],
            "prime_lineage_code": self.prime_lineage_code,
        }
        return {
            **body,
            "commitment": _sha256(body),
        }

    def behavioral_quotient(self) -> "BehavioralTrace":
        stack: list[HistoryStep] = []
        for step in self.steps:
            if stack and step.is_exact_inverse_of(stack[-1]):
                stack.pop()
            else:
                stack.append(step)
        return BehavioralTrace(
            self.subject_id,
            tuple(stack),
        )


@dataclass(frozen=True)
class BehavioralTrace:
    subject_id: str
    reduced_steps: tuple[HistoryStep, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "subject_id",
            _nonempty(self.subject_id, "subject_id"),
        )
        steps = tuple(self.reduced_steps)
        current: str | None = None
        for step in steps:
            if not isinstance(step, HistoryStep):
                raise MemoryOntologyAlgebraError(
                    "reduced_steps must contain HistoryStep"
                )
            if current is not None and step.source_id != current:
                raise MemoryOntologyAlgebraError(
                    "behavioral trace endpoints do not compose"
                )
            current = step.target_id
        object.__setattr__(self, "reduced_steps", steps)

    def behavioral_signature(self) -> dict[str, Any]:
        body = {
            "subject_id": self.subject_id,
            "reduced_path": [
                {
                    "edge_id": step.edge_id,
                    "source_id": step.source_id,
                    "target_id": step.target_id,
                }
                for step in self.reduced_steps
            ],
        }
        return {
            **body,
            "commitment": _sha256(body),
        }


# ---------------------------------------------------------------------------
# Typed representation morphisms / witnessed behavioral core
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TypedMorphism:
    morphism_id: str
    source_id: str
    target_id: str
    observable: str
    distance: str
    error_bound: Any
    horizon: int
    source_sector: str
    target_sector: str
    lineage: tuple[int, ...] = ()
    invariant_preserved: bool = True
    provenance_preserved: bool = True
    invertible_on_declared_image: bool = False
    total_on_declared_domain: bool = True

    def __post_init__(self) -> None:
        for field in (
            "morphism_id",
            "source_id",
            "target_id",
            "observable",
            "distance",
            "source_sector",
            "target_sector",
        ):
            object.__setattr__(
                self,
                field,
                _nonempty(getattr(self, field), field),
            )
        object.__setattr__(
            self,
            "error_bound",
            _error_fraction(self.error_bound),
        )
        if (
            isinstance(self.horizon, bool)
            or not isinstance(self.horizon, int)
            or self.horizon < 1
        ):
            raise MemoryOntologyAlgebraError(
                "horizon must be a positive integer"
            )
        line = tuple(self.lineage)
        for symbol in line:
            _positive_int(symbol, "lineage symbol")
        object.__setattr__(self, "lineage", line)

    @property
    def history_code(self) -> int:
        return encode_prime_word(self.lineage)

    def behavioral_signature(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "observable": self.observable,
            "distance": self.distance,
            "error_bound": {
                "numerator": self.error_bound.numerator,
                "denominator": self.error_bound.denominator,
            },
            "horizon": self.horizon,
            "source_sector": self.source_sector,
            "target_sector": self.target_sector,
            "invariant_preserved": self.invariant_preserved,
            "invertible_on_declared_image":
                self.invertible_on_declared_image,
            "total_on_declared_domain":
                self.total_on_declared_domain,
        }

    def historical_signature(self) -> dict[str, Any]:
        return {
            **self.behavioral_signature(),
            "lineage": list(self.lineage),
            "history_code": self.history_code,
            "provenance_preserved": self.provenance_preserved,
        }


@dataclass(frozen=True)
class BehavioralInverseWitness:
    witness_id: str
    forward_id: str
    inverse_id: str
    validator: str
    validator_receipt: str
    left_identity_verified: bool
    right_identity_verified: bool
    domain_image_verified: bool

    def __post_init__(self) -> None:
        for field in (
            "witness_id",
            "forward_id",
            "inverse_id",
            "validator",
            "validator_receipt",
        ):
            object.__setattr__(
                self,
                field,
                _nonempty(getattr(self, field), field),
            )
        if self.forward_id == self.inverse_id:
            raise MemoryOntologyAlgebraError(
                "inverse witness requires distinct arrows"
            )
        if not (
            self.left_identity_verified is True
            and self.right_identity_verified is True
            and self.domain_image_verified is True
        ):
            raise MemoryOntologyAlgebraError(
                "inverse witness must verify both identities and domain/image"
            )


def certified_behavioral_core(
    morphisms: Iterable[TypedMorphism],
    witnesses: Iterable[BehavioralInverseWitness],
) -> dict[str, Any]:
    by_id: dict[str, TypedMorphism] = {}
    for morphism in morphisms:
        if not isinstance(morphism, TypedMorphism):
            raise MemoryOntologyAlgebraError(
                "morphisms must contain TypedMorphism"
            )
        if morphism.morphism_id in by_id:
            raise MemoryOntologyAlgebraError(
                f"duplicate morphism {morphism.morphism_id}"
            )
        by_id[morphism.morphism_id] = morphism

    admitted: set[str] = set()
    pairs: set[tuple[str, str]] = set()

    for witness in tuple(witnesses):
        if not isinstance(witness, BehavioralInverseWitness):
            raise MemoryOntologyAlgebraError(
                "witnesses must contain BehavioralInverseWitness"
            )
        try:
            forward = by_id[witness.forward_id]
            inverse = by_id[witness.inverse_id]
        except KeyError as exc:
            raise MemoryOntologyAlgebraError(
                "inverse witness references unknown morphism"
            ) from exc

        if (
            forward.source_id != inverse.target_id
            or forward.target_id != inverse.source_id
        ):
            raise MemoryOntologyAlgebraError(
                "inverse endpoints are not reversed"
            )
        if (
            forward.source_sector != inverse.target_sector
            or forward.target_sector != inverse.source_sector
        ):
            raise MemoryOntologyAlgebraError(
                "inverse sectors are not reversed"
            )
        if (
            forward.observable != inverse.observable
            or forward.distance != inverse.distance
        ):
            raise MemoryOntologyAlgebraError(
                "inverse behavioral contracts differ"
            )
        if forward.error_bound != 0 or inverse.error_bound != 0:
            raise MemoryOntologyAlgebraError(
                "behavioral core requires exact zero-error inverse pairs"
            )
        if not (
            forward.invertible_on_declared_image
            and inverse.invertible_on_declared_image
        ):
            raise MemoryOntologyAlgebraError(
                "both arrows must declare local invertibility"
            )
        if not (
            forward.invariant_preserved
            and inverse.invariant_preserved
            and forward.provenance_preserved
            and inverse.provenance_preserved
        ):
            raise MemoryOntologyAlgebraError(
                "inverse pair failed invariant/provenance admission"
            )

        admitted.update(
            (forward.morphism_id, inverse.morphism_id)
        )
        pairs.add(
            tuple(
                sorted(
                    (forward.morphism_id, inverse.morphism_id)
                )
            )
        )

    excluded = sorted(
        morphism.morphism_id
        for morphism in by_id.values()
        if morphism.invertible_on_declared_image
        and morphism.morphism_id not in admitted
    )
    return {
        "schema": "GREMLIN_CERTIFIED_BEHAVIORAL_CORE_V0_1",
        "morphism_ids": sorted(admitted),
        "inverse_pairs": sorted(pairs),
        "excluded_unwitnessed_invertible_ids": excluded,
        "witness_required": True,
        "maximal_core_claim": False,
    }


# ---------------------------------------------------------------------------
# Exact ternary path sector -> integer winding lift -> U(1) character
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntegerPath:
    coeffs: tuple[int, ...]

    def __post_init__(self) -> None:
        coeffs = tuple(self.coeffs)
        if not coeffs:
            raise MemoryOntologyAlgebraError(
                "path cannot be empty"
            )
        if any(
            isinstance(x, bool) or not isinstance(x, int)
            for x in coeffs
        ):
            raise MemoryOntologyAlgebraError(
                "integer path coefficients must be integers"
            )
        object.__setattr__(self, "coeffs", coeffs)


@dataclass(frozen=True)
class TernaryPath:
    coeffs: tuple[int, ...]

    def __post_init__(self) -> None:
        coeffs = tuple(self.coeffs)
        if not coeffs:
            raise MemoryOntologyAlgebraError(
                "path cannot be empty"
            )
        if any(x not in TRITS for x in coeffs):
            raise MemoryOntologyAlgebraError(
                "ternary coefficients must be in {-1,0,+1}"
            )
        object.__setattr__(self, "coeffs", coeffs)

    def compose(
        self,
        other: "TernaryPath",
    ) -> "TernaryPath | IntegerPath":
        if not isinstance(other, TernaryPath):
            raise MemoryOntologyAlgebraError(
                "TernaryPath required"
            )
        if len(self.coeffs) != len(other.coeffs):
            raise MemoryOntologyAlgebraError(
                "path dimensions differ"
            )
        summed = tuple(
            a + b
            for a, b in zip(self.coeffs, other.coeffs)
        )
        if all(x in TRITS for x in summed):
            return TernaryPath(summed)
        return IntegerPath(summed)


def path_boundary(
    incidence: Sequence[Sequence[int]],
    path: TernaryPath | IntegerPath,
) -> tuple[int, ...]:
    if not incidence:
        raise MemoryOntologyAlgebraError(
            "incidence matrix cannot be empty"
        )
    width = len(path.coeffs)
    out: list[int] = []
    for row in incidence:
        if len(row) != width:
            raise MemoryOntologyAlgebraError(
                "incidence/path dimension mismatch"
            )
        out.append(
            sum(
                int(b) * int(t)
                for b, t in zip(row, path.coeffs)
            )
        )
    return tuple(out)


def path_phase(
    path: TernaryPath | IntegerPath,
    edge_phases: Sequence[float],
) -> float:
    if len(path.coeffs) != len(edge_phases):
        raise MemoryOntologyAlgebraError(
            "phase/path dimension mismatch"
        )
    values = tuple(float(x) for x in edge_phases)
    if not all(math.isfinite(x) for x in values):
        raise MemoryOntologyAlgebraError(
            "edge phases must be finite"
        )
    value = math.fsum(
        coefficient * theta
        for coefficient, theta in zip(path.coeffs, values)
    ) % TAU
    if math.isclose(value, TAU, rel_tol=0.0, abs_tol=1e-12):
        return 0.0
    return value


def path_holonomy(
    path: TernaryPath | IntegerPath,
    edge_phases: Sequence[float],
) -> complex:
    return cmath.exp(1j * path_phase(path, edge_phases))


# ---------------------------------------------------------------------------
# GREMLIN integration contract
# ---------------------------------------------------------------------------

def memory_ontology_manifest() -> dict[str, Any]:
    body = {
        "schema": SCHEMA,
        "version": VERSION,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "main_commit": SOURCE_MAIN_COMMIT,
            "blobs": dict(SOURCE_BLOBS),
            "receipt_status": SOURCE_RECEIPT_STATUS,
            "receipt_gate": dict(SOURCE_RECEIPT_GATE),
        },
        "structural_model": {
            "historical_layer":
                "RAW_VALIDATED_HISTORY_CATEGORY",
            "behavioral_layer":
                "EXACT_BACKTRACKING_QUOTIENT",
            "representation_layer":
                "PARTIAL_TYPED_REPRESENTATION_MORPHISMS",
            "invertible_core":
                "WITNESS_GATED_UNDER_APPROXIMATION",
            "ternary_sector":
                "EXACT_SIGNED_PATH_SECTOR_WITH_INTEGER_OVERFLOW_LIFT",
            "phase_character":
                "U1_HOLONOMY_EXP_I_DOT",
        },
        "role_bindings": dict(MEMORY_ONTOLOGY_ROLE_BINDINGS),
        "claims": {
            "source_bound": True,
            "global_groupoid": False,
            "maximal_core": False,
            "collatz_convergence": False,
            "physical_quantum_claim": False,
            "physical_ternary_claim": False,
            "automatic_hive_mutation": False,
            "production_runtime_write": False,
            "canon_allowed": False,
        },
    }
    return {
        **body,
        "manifest_sha256": _sha256(body),
    }


def build_memory_ontology_handoff(
    *,
    subject_id: str,
    generation_id: str,
    task_id: str,
    context_commitment: str | None = None,
    historical_trace: HistoricalTrace | None = None,
    morphisms: Iterable[TypedMorphism] = (),
    witnesses: Iterable[BehavioralInverseWitness] = (),
) -> dict[str, Any]:
    subject = _nonempty(subject_id, "subject_id")
    generation = _nonempty(generation_id, "generation_id")
    task = _nonempty(task_id, "task_id")

    if context_commitment is not None:
        context_commitment = _nonempty(
            context_commitment,
            "context_commitment",
        )

    trace = (
        historical_trace
        if historical_trace is not None
        else HistoricalTrace(subject)
    )
    if trace.subject_id != subject:
        raise MemoryOntologyAlgebraError(
            "historical trace subject mismatch"
        )

    historical = trace.historical_signature()
    behavioral = trace.behavioral_quotient().behavioral_signature()
    morphism_rows = tuple(morphisms)
    witness_rows = tuple(witnesses)
    core = certified_behavioral_core(
        morphism_rows,
        witness_rows,
    )

    manifest = memory_ontology_manifest()
    payload = {
        "schema": "GREMLIN_MEMORY_ONTOLOGY_HANDOFF_V0_1",
        "source_contract_sha256":
            manifest["manifest_sha256"],
        "subject_id": subject,
        "generation_id": generation,
        "task_id": task,
        "context_commitment": context_commitment,
        "historical_signature": historical,
        "behavioral_signature": behavioral,
        "representation_morphisms": [
            {
                "morphism_id": m.morphism_id,
                "behavioral": m.behavioral_signature(),
                "historical": m.historical_signature(),
            }
            for m in morphism_rows
        ],
        "certified_behavioral_core": core,
        "analysis_route_mask": [
            "SPIDER",
            "RAVEN",
            "HOUND",
            "MOLE",
            "OWL",
            "MANTIS",
        ],
        "memory_followup_roles": [
            "ELEPHANT",
            "BEES",
        ],
        "representation_transform_role": "CHAMELEON",
        "synthesis_role": "BELZEBUB",
        "aggregate_role": "GREMLIN",
        "execution_semantics": {
            "history_erased_by_behavioral_quotient": False,
            "behavioral_backtracking_reduction": True,
            "equal_symbol_implies_inverse": False,
            "silent_mod3": False,
            "ternary_overflow": "INTEGER_WINDING_LIFT",
            "witness_required_for_behavioral_core": True,
            "automatic_hive_mutation": False,
        },
        "authority": "CANDIDATE_ONLY",
        "canon_allowed": False,
    }
    payload["handoff_sha256"] = _sha256(payload)
    return payload


__all__ = [
    "SCHEMA",
    "VERSION",
    "SOURCE_REPOSITORY",
    "SOURCE_MAIN_COMMIT",
    "SOURCE_BLOBS",
    "MEMORY_ONTOLOGY_ROLE_BINDINGS",
    "MemoryOntologyAlgebraError",
    "primes_first",
    "encode_prime_word",
    "decode_prime_word",
    "prime_position_shift",
    "associate_prime_codes",
    "dissociate_prime_code",
    "HistoryStep",
    "HistoricalTrace",
    "BehavioralTrace",
    "TypedMorphism",
    "BehavioralInverseWitness",
    "certified_behavioral_core",
    "IntegerPath",
    "TernaryPath",
    "path_boundary",
    "path_phase",
    "path_holonomy",
    "memory_ontology_manifest",
    "build_memory_ontology_handoff",
]
