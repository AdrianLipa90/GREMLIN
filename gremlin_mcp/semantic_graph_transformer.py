from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
import hashlib, json, re
from typing import Any, Mapping, Sequence

SCHEMA = "GREMLIN_SEMANTIC_GRAPH_TRANSFORMER_V0_1"
VERSION = "0.1.0"
RELATION_CODES = {
    "ASSOCIATED_WITH": 1, "IS_A": 2, "PART_OF": 3, "CAUSES": 4,
    "SUPPORTS": 5, "CONTRADICTS": 6, "TRANSFORMS": 7,
    "DEPENDS_ON": 8, "PRECEDES": 9, "SAME_AS": 10,
}
_PATTERNS = (
    ("CAUSES", r"\b(?:causes?|leads?\s+to|produces?|powoduje|prowadzi\s+do)\b"),
    ("SUPPORTS", r"\b(?:supports?|confirms?|wspiera|potwierdza)\b"),
    ("CONTRADICTS", r"\b(?:contradicts?|refutes?|sprzecz\w*|obal\w*)\b"),
    ("PART_OF", r"\b(?:part\s+of|component\s+of|contains?|część|element)\b"),
    ("IS_A", r"\b(?:is\s+an?|are\s+an?|type\s+of|kind\s+of|jest|rodzaj)\b"),
    ("TRANSFORMS", r"\b(?:transforms?|converts?|maps?\s+to|przekształca|zamienia)\b"),
    ("DEPENDS_ON", r"\b(?:depends?\s+on|requires?|zależy\s+od|wymaga)\b"),
    ("SAME_AS", r"\b(?:same\s+as|equivalent\s+to|identical\s+to|równoważ\w*|tożsamy)\b"),
)
_PATTERNS = tuple((name, re.compile(pat, re.I)) for name, pat in _PATTERNS)
_WORD = re.compile(r"[^\W\d_][\w\-']*", re.UNICODE)
_SENTENCE = re.compile(r"(?<=[.!?;])\s+|\n+")
_STOP = frozenset("a an and are as at be by for from in is it of on or that the this to was were with i oraz albo ale jest są to ten ta te z ze w na do od dla jako przez się nie ma".split())

def _norm(value: str) -> str:
    return value.casefold().strip("-_'")

def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()

def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 127; n >>= 7
        out.append(b | (128 if n else 0))
        if not n: return bytes(out)

@dataclass(frozen=True)
class RelationToken:
    source: int
    relation: int
    target: int
    confidence_q8: int
    multiplicity: int

    def bytecode(self) -> bytes:
        return _varint(self.source) + _varint(self.relation) + _varint(self.target) + bytes((self.confidence_q8,)) + _varint(self.multiplicity)

class SemanticGraphTransformer:
    """Deterministic reference kernel for text -> typed relation graph compilation.

    V0.1 fixes the graph/bytecode/causal-cone contract. A learned relation scorer may
    later replace the lexical scorer without changing downstream storage semantics.
    """

    def __init__(self, *, max_neighbors: int = 8, min_confidence: float = 0.52) -> None:
        if not 1 <= int(max_neighbors) <= 128: raise ValueError("max_neighbors must be in 1..128")
        if not 0 <= float(min_confidence) <= 1: raise ValueError("min_confidence must be in 0..1")
        self.max_neighbors = int(max_neighbors); self.min_confidence = float(min_confidence)

    @staticmethod
    def _sentences(documents: Sequence[str]) -> list[str]:
        if any(not isinstance(x, str) for x in documents): raise TypeError("documents must contain strings")
        return [s.strip() for doc in documents for s in _SENTENCE.split(doc.strip()) if s.strip()]

    @staticmethod
    def _terms(sentence: str) -> list[str]:
        out, seen = [], set()
        for raw in _WORD.findall(sentence):
            token = _norm(raw)
            if len(token) >= 2 and token not in _STOP and token not in seen:
                seen.add(token); out.append(token)
        return out

    @staticmethod
    def _relation(sentence: str) -> tuple[str, float]:
        for relation, pattern in _PATTERNS:
            if pattern.search(sentence): return relation, 0.93
        return "ASSOCIATED_WITH", 0.58

    def compile(self, documents: Sequence[str]) -> dict[str, Any]:
        sentences = self._sentences(documents)
        if not sentences: raise ValueError("at least one non-empty sentence is required")
        node_counts: Counter[str] = Counter(); edges: Counter[tuple[str, str, str, int]] = Counter()
        candidate_pairs = full_pairs = 0
        for sentence in sentences:
            terms = self._terms(sentence); node_counts.update(terms); n = len(terms)
            full_pairs += n * max(0, n - 1) // 2
            relation, base = self._relation(sentence)
            for i, source in enumerate(terms):
                for j in range(i + 1, min(n, i + 1 + self.max_neighbors)):
                    candidate_pairs += 1
                    confidence = max(0.0, min(1.0, base - min(0.20, 0.025 * max(0, j-i-1)) - min(0.12, max(0, n-12)*0.006)))
                    if confidence >= self.min_confidence:
                        edges[(source, relation, terms[j], int(round(confidence*255)))] += 1
        nodes = sorted(node_counts); ids = {term:i for i,term in enumerate(nodes)}
        tokens = [RelationToken(ids[s], RELATION_CODES[r], ids[t], q8, count) for (s,r,t,q8),count in sorted(edges.items())]
        graph = {
            "nodes": [{"id":i,"term":term,"frequency":node_counts[term]} for i,term in enumerate(nodes)],
            "relations": [asdict(token) for token in tokens],
            "relation_codes": dict(RELATION_CODES),
        }
        bytecode = b"".join(token.bytecode() for token in tokens)
        occurrences = sum(edges.values()); input_bytes = sum(len(x.encode()) for x in documents)
        return {
            "schema": SCHEMA, "version": VERSION, "status": "PASS_CANDIDATE",
            "graph": graph, "bytecode_hex": bytecode.hex(), "graph_sha256": _hash(graph),
            "metrics": {
                "documents":len(documents), "sentences":len(sentences), "nodes":len(nodes),
                "unique_relation_tokens":len(tokens), "raw_relation_occurrences":occurrences,
                "repeated_edges_removed":max(0, occurrences-len(tokens)), "input_utf8_bytes":input_bytes,
                "bytecode_bytes":len(bytecode), "bytecode_to_input_ratio":len(bytecode)/input_bytes if input_bytes else 0.0,
                "candidate_pairs":candidate_pairs, "full_pair_baseline":full_pairs,
                "candidate_pair_ratio":candidate_pairs/full_pairs if full_pairs else 0.0,
                "relation_occurrence_compression_ratio":len(tokens)/occurrences if occurrences else 1.0,
            },
            "claims": {
                "bounded_neighborhood_candidate_generation":True, "full_n_squared_attention_per_sentence":False,
                "semantic_extraction_is_complete":False, "neural_transformer_trained":False, "canon_allowed":False,
            },
        }

    @staticmethod
    def causal_cone(compiled: Mapping[str, Any], seeds: Sequence[str | int], *, depth: int = 2) -> dict[str, Any]:
        if not 0 <= int(depth) <= 32: raise ValueError("depth must be in 0..32")
        graph = compiled.get("graph")
        if not isinstance(graph, Mapping): raise ValueError("compiled graph missing")
        nodes, relations = graph.get("nodes"), graph.get("relations")
        if not isinstance(nodes, list) or not isinstance(relations, list): raise ValueError("invalid compiled graph")
        by_term = {str(row["term"]):int(row["id"]) for row in nodes}; valid = set(by_term.values()); seed_ids=set()
        for seed in seeds:
            sid = seed if isinstance(seed,int) else by_term.get(_norm(str(seed)))
            if sid not in valid: raise KeyError(seed)
            seed_ids.add(int(sid))
        adj: dict[int,set[int]] = defaultdict(set)
        for row in relations:
            s,t=int(row["source"]),int(row["target"]); adj[s].add(t); adj[t].add(s)
        dist={sid:0 for sid in seed_ids}; q=deque(seed_ids)
        while q:
            node=q.popleft()
            if dist[node] >= depth: continue
            for nxt in sorted(adj.get(node,())):
                if nxt not in dist: dist[nxt]=dist[node]+1; q.append(nxt)
        active=set(dist)
        out_nodes=[dict(row) for row in nodes if int(row["id"]) in active]
        out_rel=[dict(row) for row in relations if int(row["source"]) in active and int(row["target"]) in active]
        return {"schema":"GREMLIN_SEMANTIC_CAUSAL_CONE_V0_1","status":"PASS","depth":int(depth),"seed_ids":sorted(seed_ids),"nodes":out_nodes,"relations":out_rel,"metrics":{"active_nodes":len(out_nodes),"active_relations":len(out_rel),"full_nodes":len(nodes),"full_relations":len(relations)},"authority":"READ_ONLY_CANDIDATE","canon_allowed":False}

def compile_semantic_graph(documents: Sequence[str], *, max_neighbors: int = 8, min_confidence: float = 0.52) -> dict[str, Any]:
    return SemanticGraphTransformer(max_neighbors=max_neighbors, min_confidence=min_confidence).compile(documents)

__all__ = ["RELATION_CODES", "SCHEMA", "VERSION", "RelationToken", "SemanticGraphTransformer", "compile_semantic_graph"]
