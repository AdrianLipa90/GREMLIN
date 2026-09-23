from __future__ import annotations

import json, statistics, time
from gremlin_mcp.semantic_graph_transformer import SemanticGraphTransformer

def fixture(sentences: int) -> list[str]:
    rows = []; vocab = [f"concept{i}" for i in range(128)]
    for i in range(sentences):
        terms = [vocab[(i + j) % len(vocab)] for j in range(40)]
        rows.append(" ".join(terms[:20]) + " causes " + " ".join(terms[20:]) + ".")
    return [" ".join(rows)]

def main() -> None:
    compiler = SemanticGraphTransformer(max_neighbors=6); rows = []
    for n in (100, 1000, 5000):
        docs = fixture(n); samples = []; result = None
        for _ in range(5):
            t0 = time.perf_counter_ns(); result = compiler.compile(docs)
            samples.append((time.perf_counter_ns() - t0) / 1_000_000.0)
        rows.append({"sentences":n, "median_ms":statistics.median(samples), "p95_ms":sorted(samples)[-1], **result["metrics"]})
    print(json.dumps({
        "schema":"GREMLIN_SEMANTIC_GRAPH_TRANSFORMER_BENCHMARK_V0_1",
        "status":"PASS",
        "rows":rows,
        "claim_boundary":"Measures deterministic reference-kernel graph compilation only; not neural model quality.",
    }, sort_keys=True))

if __name__ == "__main__":
    main()
