import json
import math
import random
import time
from pathlib import Path

from gremlin_mcp.eisenstein_orbital_memory import (
    EisensteinOrbitalIndex,
)
from gremlin_mcp.relational_memory_encoder import (
    encode_memory_text,
    retrieve_memory,
)


def packet_for_word(word, *, jitter=0.0, seed=0):
    rng = random.Random(seed)
    phase = [0.0] * 36
    amp = [0.0] * 36
    for row, direction in enumerate(word[:6]):
        base_phase = (
            direction * math.pi / 3.0
            - row * math.pi / 3.0
        )
        for col in range(6):
            i = row * 6 + col
            phase[i] = (
                base_phase
                + rng.uniform(-jitter, jitter)
            )
            amp[i] = 1.0
    return {
        "phase36": phase,
        "amplitude36": amp,
        "semantic_commitment": (
            "route:"
            + "".join(str(int(x) % 6) for x in word)
            + f":{seed}"
        ),
    }


def structural_benchmark():
    index = EisensteinOrbitalIndex(
        hex_scale=8.0,
        base=4,
        split_primes=(7, 13, 19, 31, 37),
    )
    per_prefix = 30
    targets = []

    t0 = time.perf_counter()
    for a in range(6):
        for b in range(6):
            for c in range(6):
                prefix = (a, b, c)
                for j in range(per_prefix):
                    tail = (
                        j % 6,
                        (j // 3) % 6,
                        (j // 7) % 6,
                    )
                    word = prefix + tail
                    mid = (
                        f"{a}{b}{c}-"
                        f"{j:02d}"
                    )
                    packet = packet_for_word(
                        word,
                        jitter=0.003,
                        seed=(
                            a * 100000
                            + b * 10000
                            + c * 1000
                            + j
                        ),
                    )
                    index.add(
                        memory_id=mid,
                        ledger_record_id=(
                            "hive:" + mid
                        ),
                        packet=packet,
                        semantic_orbit_id="structural",
                    )
                    if j == 7 and (a + b + c) % 19 == 0:
                        targets.append((mid, packet))
    build_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    routes = [
        index.shortlist(
            packet,
            prefix_depth=3,
            last_digit_tolerance=0,
            min_candidates=8,
            semantic_orbit_ids=["structural"],
            prime_mode="off",
        )
        for _, packet in targets
    ]
    route_s = time.perf_counter() - t0

    inclusion = sum(
        target in route["candidate_ids"]
        for (target, _), route in zip(
            targets,
            routes,
        )
    ) / len(targets)

    mean_candidates = sum(
        len(route["candidate_ids"])
        for route in routes
    ) / len(routes)

    return {
        "dataset": (
            "SYNTHETIC_216_PREFIXES_X_30"
        ),
        "memories": index.count,
        "queries": len(targets),
        "build_seconds": build_s,
        "routing_seconds": route_s,
        "target_inclusion": inclusion,
        "mean_candidates": mean_candidates,
        "mean_fraction_evaluated": (
            mean_candidates / index.count
        ),
        "expected_prefix_population": per_prefix,
    }


def semantic_benchmark():
    memories = {
        "stella": (
            "stella octangula: two shared poles "
            "and six lateral vertices"
        ),
        "projections": (
            "six projections share the poles "
            "and expose six lateral channels each"
        ),
        "36d": (
            "36 = 6 projections x 6 "
            "relational channels"
        ),
        "moire": (
            "six projections may have distinct "
            "frequencies and slight relative rotations"
        ),
        "elephant": (
            "ELEPHANT consolidates relational memory, "
            "replay and retention"
        ),
        "bees": (
            "BEES checks overlap coherence, "
            "anti-entropy delta and reconciliation proposals"
        ),
    }
    cues = {
        "stella": [
            (
                "compound tetrahedral geometry with a common "
                "antipodal pole pair and six side points"
            ),
            (
                "two opposite poles organize six remaining "
                "vertices of the interpenetrating tetrahedra"
            ),
            (
                "dwa wspólne bieguny i sześć bocznych "
                "wierzchołków stella octangula"
            ),
        ],
        "projections": [
            (
                "six views use the same two poles, each "
                "carrying six side channels"
            ),
            (
                "each of the six slices keeps one common "
                "axis and carries six lateral degrees"
            ),
            (
                "sześć rzutów ma te same bieguny, każdy "
                "ma sześć bocznych kanałów"
            ),
        ],
        "36d": [
            (
                "thirty six dimensions factor into six views "
                "with six relation channels per view"
            ),
            "state factorizes into 6 by 6 relation coordinates",
            (
                "trzydzieści sześć wymiarów to sześć "
                "rzutów po sześć kanałów relacji"
            ),
        ],
        "moire": [
            (
                "slightly twisted layers oscillating at "
                "different rates create the interference pattern"
            ),
            (
                "small angular offsets plus unequal carrier "
                "rates produce a beat pattern"
            ),
            (
                "lekko obrócone warstwy z różnymi "
                "częstotliwościami tworzą interferencję moire"
            ),
        ],
        "elephant": [
            (
                "long-term memory is strengthened through "
                "consolidation, replay and retention planning"
            ),
            (
                "rehearsal and retention deepen "
                "the memory trace"
            ),
            (
                "słoń odpowiada za konsolidację pamięci, "
                "replay i retencję"
            ),
        ],
        "bees": [
            (
                "distributed fragments are compared for overlap "
                "consistency and proposed anti-entropy reconciliation"
            ),
            (
                "replicas are checked for consistency and an "
                "anti entropy repair is only proposed"
            ),
            (
                "pszczoły sprawdzają spójność nakładających "
                "się śladów i proponują rekoncyliację"
            ),
        ],
    }

    candidates = dict(memories)
    topics = (
        "compiler parser transaction ledger cache scheduler "
        "protein lattice spectrum molecule telescope orbit "
        "database network transport geometry algebra signal "
        "control runtime evidence branch validator storage "
        "policy graph context vector kernel relation"
    ).split()
    for i in range(1200):
        a = topics[i % len(topics)]
        b = topics[(i * 7 + 3) % len(topics)]
        c = topics[(i * 11 + 5) % len(topics)]
        candidates[f"noise-{i:04d}"] = (
            f"{a} {b} {c} synthetic distractor "
            f"cluster {i % 97} channel {i % 31}"
        )

    encoded = {
        mid: encode_memory_text(text)
        for mid, text in candidates.items()
    }

    index = EisensteinOrbitalIndex(
        hex_scale=9.0,
        base=4,
        split_primes=(7, 13, 19, 31, 37, 43),
    )
    for mid, packet in encoded.items():
        index.add(
            memory_id=mid,
            ledger_record_id="hive:" + mid,
            packet=packet,
        )

    queries = [
        (expected, cue)
        for expected, variants in cues.items()
        for cue in variants
    ]

    t0 = time.perf_counter()
    baseline = [
        retrieve_memory(
            cue,
            candidates,
            min_score=0.0,
            min_margin=0.0,
        )
        for _, cue in queries
    ]
    baseline_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    routed = [
        index.retrieve_reference(
            encode_memory_text(cue),
            prefix_depth=3,
            last_digit_tolerance=1,
            min_candidates=48,
            prime_mode="off",
        )
        for _, cue in queries
    ]
    routed_s = time.perf_counter() - t0

    baseline_picks = [
        row["picked"] for row in baseline
    ]
    routed_picks = [
        row["picked"] for row in routed
    ]
    expected = [
        x[0] for x in queries
    ]

    return {
        "dataset": (
            "EXISTING_18_PARAPHRASES_PLUS_1200_DISTRACTORS"
        ),
        "memories": len(candidates),
        "queries": len(queries),
        "baseline_seconds": baseline_s,
        "routed_seconds": routed_s,
        "top1_agreement_with_full": sum(
            a == b
            for a, b in zip(
                baseline_picks,
                routed_picks,
            )
        ) / len(queries),
        "expected_accuracy_full": sum(
            a == b
            for a, b in zip(
                baseline_picks,
                expected,
            )
        ) / len(queries),
        "expected_accuracy_routed": sum(
            a == b
            for a, b in zip(
                routed_picks,
                expected,
            )
        ) / len(queries),
        "mean_candidates": sum(
            row["evaluated"]
            for row in routed
        ) / len(routed),
        "mean_fraction_evaluated": sum(
            row["fraction_evaluated"]
            for row in routed
        ) / len(routed),
        "prefix_depths_used": [
            row["routing"]["prefix_depth_used"]
            for row in routed
        ],
    }


def main():
    out = {
        "schema": (
            "GREMLIN_EISENSTEIN_ORBITAL_"
            "MEMORY_BENCHMARK_V0_2"
        ),
        "structural": structural_benchmark(),
        "semantic": semantic_benchmark(),
        "claim_scope": (
            "candidate routing benchmark only; "
            "no production or biological-memory claim"
        ),
    }
    path = Path(__file__).with_name(
        "GREMLIN_EISENSTEIN_ORBITAL_MEMORY_"
        "BENCHMARK_V0_2.json"
    )
    path.write_text(
        json.dumps(out, indent=2) + "\n"
    )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
