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
    "behavioral_core_v04": "fca0fc613be268bd085bc37892242f269529fba2",
    "prime_hilbert_collatz_association": "6c517c04ab1518c2bc746222ed2a00d7113e7c12",
    "orbital_ternary_memory_algebra": "421db4ca0ab5b7ca6c876c5744552969caef5a81",
    "final_receipt": "7402cc9c3ce8c5d2ba61942f709fb2c26f8e4e77",
}
TRITS = (-1, 0, 1)
TAU = math.tau


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
        raise MemoryOntologyAlgebraError("value must be finite canonical JSON") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _nonempty(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MemoryOntologyAlgebraError(f"{field} must be a non-empty string")
    return value.strip()


def _positive_int(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise MemoryOntologyAlgebraError(f"{field} must be a positive integer")
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
            raise MemoryOntologyAlgebraError("error bound must be finite")
        out = Fraction(str(value))
    elif isinstance(value, str):
        try:
            out = Fraction(value)
        except Exception as exc:
            raise MemoryOntologyAlgebraError("invalid rational error bound") from exc
    else:
        raise MemoryOntologyAlgebraError("unsupported error bound type")
    if out < 0:
        raise MemoryOntologyAlgebraError("error bound must be non-negative")
    return out


def primes_first(count: int) -> tuple[int, ...]:
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise MemoryOntologyAlgebraError("count must be a non-negative integer")
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
        raise MemoryOntologyAlgebraError("offset must be a non-negative integer")
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
    shifted = left_code * prime_position_shift(right_code, len(left))
    if direct != shifted:
        raise AssertionError("prime/Hilbert association identity failed")
    return direct


def dissociate_prime_code(code: int, cut: int) -> tuple[int, int]:
    word = decode_prime_word(code)
    if isinstance(cut, bool) or not isinstance(cut, int) or not 0 <= cut <= len(word):
        raise MemoryOntologyAlgebraError("cut must lie in [0, word_length]")
    return encode_prime_word(word[:cut]), encode_prime_word(word[cut:])


@dataclass(frozen=True)
class HistoryStep:
    """One validated historical edge.

    inverse_edge_id is explicit. Equal symbol/edge classes never imply
    invertibility on their own.
    """

    edge_id: str
    source_id: str
    target_id: str
    symbol_code: int
    inverse_edge_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "edge_id", _nonempty(self.edge_id, "edge_id"))
        object.__setattr__(self, "source_id", _nonempty(self.source_id, "source_id"))
        object.__setattr__(self, "target_id", _nonempty(self.target_id, "target_id"))
        _positive_int(self.symbol_code, "symbol_code")
        if self.inverse_edge_id is not None:
            object.__setattr__(
                self,
                "inverse_edge_id",
                _nonempty(self.inverse_edge_id, "inverse_edge_id"),
            )

    def is_exact_inverse_of(self, previous: "HistoryStep") -> bool:
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
        object.__setattr__(self, "subject_id", _nonempty(self.subject_id, "subject_id"))
        steps = tuple(self.steps)
        current: str | None = None
        for step in steps:
            if not isinstance(step, HistoryStep):
                raise MemoryOntologyAlgebraError("steps must contain HistoryStep")
            if current is not None and step.source_id != current:
                raise MemoryOntologyAlgebraError("historical trace endpoints do not compose")
            current = step.target_id
        object.__setattr__(self, "steps", steps)

    @property
    def prime_lineage_code(self) -> int:
        return encode_prime_word(step.symbol_code for step in self.steps)

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
        return {**body, "commitment": _sha256(body)}

    def behavioral_quotient(self) -> "BehavioralTrace":
        stack: list[HistoryStep] = []
        for step in self.steps:
            if stack and step.is_exact_inverse_of(stack[-1]):
                stack.pop()
            else:
                stack.append(step)
        return BehavioralTrace(self.subject_id, tuple(stack))


@dataclass(frozen=True)
class BehavioralTrace:
    subject_id: str
    reduced_steps: tuple[HistoryStep, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "subject_id", _nonempty(self.subject_id, "subject_id"))
        object.__setattr__(self, "reduced_steps", tuple(self.reduced_steps))

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
        return {$ÑPÐ€L@