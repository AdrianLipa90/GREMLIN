from __future__ import annotations

from dataclasses import dataclass
import cmath
import hashlib
import math
from typing import Any, Iterable, Mapping, Sequence

from .holo_memory import HoloMemoryIndex, hex_distance, hex_embedding
from .relational_memory_encoder import memory_similarity

DIM = 36
ROWS = 6
COLS = 6
SCHEMA = "GREMLIN_EISENSTEIN_ORBITAL_MEMORY_V0_2"
AUTHORITY = {
    "source_of_truth": False,
    "ledger_mutation": False,
    "canon_allowed": False,
    "derived_index_only": True,
}

DEFAULT_SPLIT_PRIMES = (
    7, 13, 19, 31, 37, 43, 61, 67, 73, 79, 97, 103
)


class EisensteinMemoryError(ValueError):
    pass


@dataclass(frozen=True, order=True)
class EisensteinInt:
    """a + b*omega, where omega^2 + omega + 1 = 0."""

    a: int
    b: int

    def __add__(self, other: "EisensteinInt") -> "EisensteinInt":
        return EisensteinInt(self.a + other.a, self.b + other.b)

    def __sub__(self, other: "EisensteinInt") -> "EisensteinInt":
        return EisensteinInt(self.a - other.a, self.b - other.b)

    def __neg__(self) -> "EisensteinInt":
        return EisensteinInt(-self.a, -self.b)

    def __mul__(self, other: "EisensteinInt") -> "EisensteinInt":
        return EisensteinInt(
            self.a * other.a - self.b * other.b,
            self.a * other.b
            + self.b * other.a
            - self.b * other.b,
        )

    def scale(self, scalar: int) -> "EisensteinInt":
        return EisensteinInt(
            int(scalar) * self.a,
            int(scalar) * self.b,
        )

    @property
    def norm(self) -> int:
        return self.a * self.a - self.a * self.b + self.b * self.b

    @property
    def hex_radius(self) -> int:
        return max(
            abs(self.a),
            abs(self.b),
            abs(self.a - self.b),
        )

    def to_complex(self) -> complex:
        return complex(
            self.a - 0.5 * self.b,
            (math.sqrt(3.0) / 2.0) * self.b,
        )


# Six Eisenstein units ordered cyclically by 60 degrees.
# 1+omega = -omega^2.
EISENSTEIN_UNITS: tuple[EisensteinInt, ...] = (
    EisensteinInt(1, 0),
    EisensteinInt(1, 1),
    EisensteinInt(0, 1),
    EisensteinInt(-1, 0),
    EisensteinInt(-1, -1),
    EisensteinInt(0, -1),
)


def eisenstein_unit(direction: int) -> EisensteinInt:
    if not isinstance(direction, int):
        raise EisensteinMemoryError("direction must be an integer")
    return EISENSTEIN_UNITS[direction % 6]


def centered_hex_count(radius: int) -> int:
    n = int(radius)
    if n < 0:
        raise EisensteinMemoryError("radius must be >= 0")
    return 3 * n * n + 3 * n + 1


def centered_hex_eisenstein(radius: int) -> EisensteinInt:
    n = int(radius)
    if n < 0:
        raise EisensteinMemoryError("radius must be >= 0")
    z = EisensteinInt(n + 1, -n)
    if z.norm != centered_hex_count(n):
        raise AssertionError("centered-hex norm identity failed")
    return z


def _is_prime(value: int) -> bool:
    n = int(value)
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    k = 5
    while k * k <= n:
        if n % k == 0 or n % (k + 2) == 0:
            return False
        k += 6
    return True


def _mod_sqrt_prime(a: int, p: int) -> int:
    """Tonelli-Shanks for an odd prime p; returns one square root."""
    a %= p
    if a == 0:
        return 0
    if p == 2:
        return a
    if pow(a, (p - 1) // 2, p) != 1:
        raise EisensteinMemoryError(
            "value is not a quadratic residue modulo p"
        )
    if p % 4 == 3:
        return pow(a, (p + 1) // 4, p)

    q = p - 1
    s = 0
    while q % 2 == 0:
        s += 1
        q //= 2

    z = 2
    while pow(z, (p - 1) // 2, p) != p - 1:
        z += 1

    m = s
    c = pow(z, q, p)
    t = pow(a, q, p)
    r = pow(a, (q + 1) // 2, p)

    while t != 1:
        i = 1
        tt = (t * t) % p
        while tt != 1:
            tt = (tt * tt) % p
            i += 1
            if i >= m:
                raise EisensteinMemoryError(
                    "Tonelli-Shanks failed"
                )
        b = pow(c, 1 << (m - i - 1), p)
        r = (r * b) % p
        c = (b * b) % p
        t = (t * c) % p
        m = i
    return r


def split_prime_roots(prime: int) -> tuple[int, int]:
    q = int(prime)
    if q <= 3 or q % 6 != 1 or not _is_prime(q):
        raise EisensteinMemoryError(
            "prime channel requires prime q congruent to 1 mod 6"
        )
    root = _mod_sqrt_prime(-3, q)
    inv6 = pow(6, -1, q)
    roots = tuple(
        sorted(
            {
                ((-3 + root) * inv6) % q,
                ((-3 - root) * inv6) % q,
            }
        )
    )
    if len(roots) != 2:
        raise AssertionError(
            "split prime must yield exactly two radial roots"
        )
    if any(centered_hex_count(n) % q for n in roots):
        raise AssertionError(
            "prime-channel root verification failed"
        )
    return roots  # type: ignore[return-value]


def prime_channel_signature(
    radius: int,
    *,
    primes: Sequence[int] = DEFAULT_SPLIT_PRIMES,
) -> tuple[int, ...]:
    n = int(radius)
    if n < 0:
        raise EisensteinMemoryError("radius must be >= 0")
    active: list[int] = []
    seen: set[int] = set()
    for value in primes:
        q = int(value)
        if q in seen:
            continue
        seen.add(q)
        roots = split_prime_roots(q)
        if n % q in roots:
            active.append(q)
    return tuple(active)


def _validate_base(base: int) -> None:
    if not isinstance(base, int) or base < 4:
        raise EisensteinMemoryError(
            "recursive Eisenstein base must be integer >= 4"
        )


@dataclass(frozen=True)
class RecursiveEisensteinAddress:
    base: int
    word: tuple[int, ...]
    code: EisensteinInt

    @classmethod
    def root(
        cls,
        *,
        base: int = 4,
    ) -> "RecursiveEisensteinAddress":
        _validate_base(base)
        return cls(
            int(base),
            (),
            EisensteinInt(0, 0),
        )

    @classmethod
    def from_word(
        cls,
        word: Sequence[int],
        *,
        base: int = 4,
    ) -> "RecursiveEisensteinAddress":
        address = cls.root(base=base)
        for direction in word:
            address = address.append(int(direction))
        return address

    @property
    def depth(self) -> int:
        return len(self.word)

    def append(
        self,
        direction: int,
    ) -> "RecursiveEisensteinAddress":
        unit = eisenstein_unit(int(direction))
        return RecursiveEisensteinAddress(
            self.base,
            self.word + (int(direction) % 6,),
            self.code.scale(self.base) + unit,
        )

    def prefix(
        self,
        depth: int,
    ) -> "RecursiveEisensteinAddress":
        d = int(depth)
        if d < 0 or d > self.depth:
            raise EisensteinMemoryError(
                "prefix depth out of range"
            )
        return RecursiveEisensteinAddress.from_word(
            self.word[:d],
            base=self.base,
        )

    @property
    def poincare_radius_sq_fraction(self) -> tuple[int, int]:
        if self.depth == 0:
            return (0, 1)
        numerator = (
            (self.base - 1)
            * (self.base - 1)
            * self.code.norm
        )
        denominator = self.base ** (2 * self.depth)
        return numerator, denominator

    @property
    def poincare_radius(self) -> float:
        num, den = self.poincare_radius_sq_fraction
        return math.sqrt(num / den)

    def poincare_point(self) -> complex:
        if self.depth == 0:
            return 0j
        return (
            (self.base - 1)
            / (self.base ** self.depth)
            * self.code.to_complex()
        )

    @property
    def boundary_gap(self) -> float:
        return 1.0 - self.poincare_radius


def _phase_packet(
    packet: Mapping[str, Any],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    phase = packet.get("phase36")
    amp = packet.get("amplitude36")
    if not isinstance(phase, Sequence) or len(phase) != DIM:
        raise EisensteinMemoryError(
            "packet requires exact phase36"
        )
    if not isinstance(amp, Sequence) or len(amp) != DIM:
        raise EisensteinMemoryError(
            "packet requires exact amplitude36"
        )
    p = tuple(float(x) for x in phase)
    a = tuple(float(x) for x in amp)
    if not all(math.isfinite(x) for x in p + a):
        raise EisensteinMemoryError(
            "phase/amplitude must be finite"
        )
    if any(x < 0 for x in a):
        raise EisensteinMemoryError(
            "amplitudes must be non-negative"
        )
    return p, a


def _nearest_hex_direction(angle: float) -> int:
    step = math.pi / 3.0
    return int(
        math.floor((angle + step / 2.0) / step)
    ) % 6


def _semantic_route_atoms(
    packet: Mapping[str, Any],
) -> tuple[tuple[str, int], ...]:
    concepts = tuple(
        str(x)
        for x in packet.get("concept_atoms", ())
        if str(x)
    )
    numeric = tuple(
        str(x)
        for x in packet.get("numeric_atoms", ())
        if str(x)
    )
    lexical = tuple(
        str(x)
        for x in packet.get("lexical_atoms", ())
        if str(x)
    )

    # Same relative weights as the relational-memory scorer,
    # multiplied by two to obtain exact integer replication counts:
    # concept 3 -> 6, numeric 2 -> 4, lexical 0.5 -> 1.
    if concepts or numeric:
        atoms = (
            [(atom, 6) for atom in concepts]
            + [(atom, 4) for atom in numeric]
        )
    else:
        atoms = [(atom, 1) for atom in lexical]
    return tuple(sorted(atoms))


def _semantic_orbital_word(
    packet: Mapping[str, Any],
) -> tuple[int, ...] | None:
    atoms = _semantic_route_atoms(packet)
    if not atoms:
        return None

    word: list[int] = []
    for level in range(ROWS):
        best_score: int | None = None
        best_digest: bytes | None = None
        for atom, replicas in atoms:
            for replica in range(replicas):
                digest = hashlib.sha256(
                    (
                        f"{SCHEMA}|SEMANTIC_LSH|{level}|"
                        f"{atom}|{replica}"
                    ).encode("utf-8")
                ).digest()
                score = int.from_bytes(
                    digest[:8],
                    "big",
                )
                if (
                    best_score is None
                    or score < best_score
                ):
                    best_score = score
                    best_digest = digest
        if best_digest is None:
            return None
        word.append(best_digest[8] % 6)
    return tuple(word)


def _phase_orbital_word(
    packet: Mapping[str, Any],
    *,
    zero_tolerance: float = 1e-15,
) -> tuple[int, ...]:
    phase, amp = _phase_packet(packet)
    word: list[int] = []
    for row in range(ROWS):
        start = row * COLS
        z = sum(
            amp[i] * cmath.exp(1j * phase[i])
            for i in range(start, start + COLS)
        ) / COLS
        if abs(z) <= zero_tolerance:
            continue
        oriented = z * cmath.exp(
            1j * row * math.pi / 3.0
        )
        word.append(
            _nearest_hex_direction(cmath.phase(oriented))
        )
    if not word:
        raise EisensteinMemoryError(
            "packet has no active projection row"
        )
    return tuple(word)


def packet_orbital_route(
    packet: Mapping[str, Any],
    *,
    zero_tolerance: float = 1e-15,
) -> tuple[tuple[int, ...], str]:
    semantic = _semantic_orbital_word(packet)
    if semantic is not None:
        return (
            semantic,
            "SEMANTIC_ATOM_WEIGHTED_MINHASH",
        )
    return (
        _phase_orbital_word(
            packet,
            zero_tolerance=zero_tolerance,
        ),
        "PHASE36_ROW_RESULTANT",
    )


def packet_orbital_word(
    packet: Mapping[str, Any],
    *,
    zero_tolerance: float = 1e-15,
) -> tuple[int, ...]:
    word, _ = packet_orbital_route(
        packet,
        zero_tolerance=zero_tolerance,
    )
    return word


def prefix_neighborhood(
    prefix: Sequence[int],
    *,
    last_digit_tolerance: int = 0,
) -> tuple[tuple[int, ...], ...]:
    p = tuple(int(x) % 6 for x in prefix)
    tolerance = int(last_digit_tolerance)
    if tolerance < 0 or tolerance > 2:
        raise EisensteinMemoryError(
            "last_digit_tolerance must be in [0,2]"
        )
    if not p or tolerance == 0:
        return (p,)
    head = p[:-1]
    last = p[-1]
    variants = {
        head + ((last + delta) % 6,)
        for delta in range(
            -tolerance,
            tolerance + 1,
        )
    }
    return tuple(sorted(variants))


@dataclass(frozen=True)
class EisensteinOrbitalCell:
    memory_id: str
    ledger_record_id: str
    word: tuple[int, ...]
    code_a: int
    code_b: int
    depth: int
    poincare_radius: float
    coarse_hex_q: int
    coarse_hex_r: int
    coarse_shell_radius: int
    centered_hex_cells: int
    coarse_prime_channels: tuple[int, ...]
    trajectory_radius: int
    trajectory_prime_channels: tuple[int, ...]
    priority_orbit_index: int
    semantic_orbit_id: str | None
    semantic_commitment: str
    route_source: str


class EisensteinOrbitalIndex:
    """Recursive Eisenstein addressing over HoloMemory v0.1."""

    def __init__(
        self,
        *,
        hex_scale: float = 9.0,
        base: int = 4,
        split_primes: Sequence[int] = DEFAULT_SPLIT_PRIMES,
    ) -> None:
        _validate_base(base)
        self.base = int(base)
        self.split_primes = tuple(
            dict.fromkeys(int(q) for q in split_primes)
        )
        for q in self.split_primes:
            split_prime_roots(q)
        self.holo = HoloMemoryIndex(
            hex_scale=hex_scale
        )
        self._cells: dict[
            str,
            EisensteinOrbitalCell,
        ] = {}
        self._packets: dict[
            str,
            dict[str, Any],
        ] = {}
        self._prefix: dict[
            tuple[int, ...],
            list[str],
        ] = {}

    @property
    def count(self) -> int:
        return len(self._cells)

    def add(
        self,
        *,
        memory_id: str,
        ledger_record_id: str,
        packet: Mapping[str, Any],
        priority_orbit_index: int = 0,
        semantic_orbit_id: str | None = None,
        priority: float = 0.5,
        route_word: Sequence[int] | None = None,
    ) -> EisensteinOrbitalCell:
        mid = str(memory_id).strip()
        if not mid:
            raise EisensteinMemoryError(
                "memory_id is required"
            )
        if mid in self._cells:
            raise EisensteinMemoryError(
                "duplicate memory_id"
            )

        holo_cell = self.holo.add(
            memory_id=mid,
            ledger_record_id=ledger_record_id,
            packet=packet,
            priority_orbit_index=priority_orbit_index,
            semantic_orbit_id=semantic_orbit_id,
            priority=priority,
        )

        if route_word is None:
            word, route_source = packet_orbital_route(
                packet
            )
        else:
            word = tuple(
                int(x) % 6
                for x in route_word
            )
            route_source = "EXPLICIT_ROUTE_WORD"
        if not word:
            raise EisensteinMemoryError(
                "route_word may not be empty"
            )

        address = (
            RecursiveEisensteinAddress.from_word(
                word,
                base=self.base,
            )
        )
        coarse_radius = hex_distance(
            (0, 0),
            (
                holo_cell.hex_q,
                holo_cell.hex_r,
            ),
        )
        trajectory_radius = (
            address.code.hex_radius
        )

        cell = EisensteinOrbitalCell(
            memory_id=mid,
            ledger_record_id=str(
                ledger_record_id
            ),
            word=word,
            code_a=address.code.a,
            code_b=address.code.b,
            depth=address.depth,
            poincare_radius=(
                address.poincare_radius
            ),
            coarse_hex_q=holo_cell.hex_q,
            coarse_hex_r=holo_cell.hex_r,
            coarse_shell_radius=coarse_radius,
            centered_hex_cells=(
                centered_hex_count(
                    coarse_radius
                )
            ),
            coarse_prime_channels=(
                prime_channel_signature(
                    coarse_radius,
                    primes=self.split_primes,
                )
            ),
            trajectory_radius=(
                trajectory_radius
            ),
            trajectory_prime_channels=(
                prime_channel_signature(
                    trajectory_radius,
                    primes=self.split_primes,
                )
            ),
            priority_orbit_index=(
                holo_cell.priority_orbit_index
            ),
            semantic_orbit_id=(
                holo_cell.semantic_orbit_id
            ),
            semantic_commitment=(
                holo_cell.semantic_commitment
            ),
            route_source=route_source,
        )

        self._cells[mid] = cell
        self._packets[mid] = dict(packet)

        for depth in range(
            1,
            len(word) + 1,
        ):
            prefix = word[:depth]
            self._prefix.setdefault(
                prefix,
                [],
            ).append(mid)
            self._prefix[prefix].sort()

        return cell

    def _filter_ids(
        self,
        ids: Iterable[str],
        *,
        semantic_orbit_ids: (
            Sequence[str] | None
        ),
    ) -> list[str]:
        out = list(
            dict.fromkeys(sorted(ids))
        )
        if semantic_orbit_ids is None:
            return out
        allowed = {
            str(x).strip()
            for x in semantic_orbit_ids
            if str(x).strip()
        }
        if not allowed:
            raise EisensteinMemoryError(
                "semantic_orbit_ids must "
                "contain a non-empty id"
            )
        return [
            mid
            for mid in out
            if (
                self._cells[
                    mid
                ].semantic_orbit_id
                in allowed
            )
        ]

    def shortlist(
        self,
        cue: Mapping[str, Any],
        *,
        prefix_depth: int = 3,
        last_digit_tolerance: int = 1,
        min_candidates: int = 8,
        semantic_orbit_ids: (
            Sequence[str] | None
        ) = None,
        prime_mode: str = "off",
        prime_radius: str = "coarse",
    ) -> dict[str, Any]:
        if min_candidates < 1:
            raise EisensteinMemoryError(
                "min_candidates must be >=1"
            )
        if prime_mode not in {
            "off",
            "filter",
        }:
            raise EisensteinMemoryError(
                "prime_mode must be off "
                "or filter"
            )
        if prime_radius not in {
            "coarse",
            "trajectory",
        }:
            raise EisensteinMemoryError(
                "prime_radius must be "
                "coarse or trajectory"
            )

        word, route_source = packet_orbital_route(cue)
        requested_depth = min(
            max(int(prefix_depth), 0),
            len(word),
        )
        depth = requested_depth
        candidates: list[str] = []

        while depth > 0:
            prefixes = prefix_neighborhood(
                word[:depth],
                last_digit_tolerance=(
                    last_digit_tolerance
                ),
            )
            raw: list[str] = []
            for prefix in prefixes:
                raw.extend(
                    self._prefix.get(
                        prefix,
                        (),
                    )
                )
            candidates = self._filter_ids(
                raw,
                semantic_orbit_ids=(
                    semantic_orbit_ids
                ),
            )
            if (
                len(candidates)
                >= min_candidates
            ):
                break
            depth -= 1

        if depth == 0:
            candidates = self._filter_ids(
                self._cells,
                semantic_orbit_ids=(
                    semantic_orbit_ids
                ),
            )

        query_address = (
            RecursiveEisensteinAddress.from_word(
                word,
                base=self.base,
            )
        )
        query_coord = hex_embedding(
            cue,
            scale=self.holo.hex_scale,
        )
        coarse_radius_value = hex_distance(
            (0, 0),
            query_coord,
        )
        trajectory_radius_value = (
            query_address.code.hex_radius
        )
        radius_value = (
            coarse_radius_value
            if prime_radius == "coarse"
            else trajectory_radius_value
        )
        query_channels = (
            prime_channel_signature(
                radius_value,
                primes=self.split_primes,
            )
        )

        prime_fallback = False
        if (
            prime_mode == "filter"
            and query_channels
        ):
            channel_set = set(
                query_channels
            )
            filtered = [
                mid
                for mid in candidates
                if channel_set.intersection(
                    (
                        self._cells[
                            mid
                        ].coarse_prime_channels
                        if prime_radius
                        == "coarse"
                        else self._cells[
                            mid
                        ].trajectory_prime_channels
                    )
                )
            ]
            if filtered:
                candidates = filtered
            else:
                prime_fallback = True

        return {
            "schema": (
                "GREMLIN_EISENSTEIN_"
                "ORBITAL_SHORTLIST_V0_2"
            ),
            "word": word,
            "route_source": route_source,
            "address": {
                "a": query_address.code.a,
                "b": query_address.code.b,
                "depth": (
                    query_address.depth
                ),
                "poincare_radius": (
                    query_address
                    .poincare_radius
                ),
            },
            "requested_prefix_depth": (
                requested_depth
            ),
            "prefix_depth_used": depth,
            "last_digit_tolerance": int(
                last_digit_tolerance
            ),
            "candidate_ids": tuple(
                candidates
            ),
            "evaluated_fraction": (
                0.0
                if not self._cells
                else (
                    len(candidates)
                    / len(self._cells)
                )
            ),
            "prime_mode": prime_mode,
            "prime_radius": prime_radius,
            "prime_channels": (
                query_channels
            ),
            "prime_fallback": (
                prime_fallback
            ),
            "coarse_shell_radius": (
                coarse_radius_value
            ),
            "trajectory_radius": (
                trajectory_radius_value
            ),
            "authority": dict(
                AUTHORITY
            ),
        }

    def retrieve_reference(
        self,
        cue: Mapping[str, Any],
        **routing: Any,
    ) -> dict[str, Any]:
        route = self.shortlist(
            cue,
            **routing,
        )
        ids = list(
            route["candidate_ids"]
        )
        ranked = []
        for mid in ids:
            sim = memory_similarity(
                cue,
                self._packets[mid],
            )
            ranked.append(
                {
                    "memory_id": mid,
                    **sim,
                }
            )
        ranked.sort(
            key=lambda row: (
                -float(row["score"]),
                row["memory_id"],
            )
        )
        return {
            "schema": (
                "GREMLIN_EISENSTEIN_"
                "ORBITAL_RETRIEVAL_V0_2"
            ),
            "status": (
                "MATCH"
                if ranked
                else "NO_CANDIDATE"
            ),
            "picked": (
                ranked[0]["memory_id"]
                if ranked
                else None
            ),
            "ranked": ranked,
            "evaluated": len(ranked),
            "total": len(self._cells),
            "fraction_evaluated": (
                route[
                    "evaluated_fraction"
                ]
            ),
            "routing": route,
            "scorer": (
                "GREMLIN_RELATIONAL_"
                "MEMORY_SIMILARITY_V0_1"
            ),
            "authority": dict(
                AUTHORITY
            ),
        }
