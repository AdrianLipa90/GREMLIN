from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from gremlin_mcp.pipeline import collect, enqueue_synthesis, fanout
from gremlin_mcp.web import research
from gremlin_mcp.workers import WorkerBroker

EXECUTOR_SCHEMA = "GREMLIN_RESEARCH_EXECUTOR_V0_1"
EXECUTOR_VERSION = "0.1.2"

# Generic discourse terms remain excluded from concept nodes. Relational verbs are
# handled separately as candidate graph operators rather than discarded as noise.
_STOPWORDS = {
    "about", "after", "against", "approach", "approaches", "between", "consider", "considered",
    "could", "evidence", "from", "into", "more", "other", "paper", "papers", "present",
    "presented", "presents", "relation", "research", "review", "show", "shown", "shows",
    "source", "sources", "studied", "studies", "study", "that", "their", "there", "these",
    "this", "through", "using", "with", "within", "would", "audit", "contradictions",
    "dependencies", "graph",
}
_RELATION_FORMS = {
    "describe": "DESCRIBES",
    "described": "DESCRIBES",
    "describes": "DESCRIBES",
    "relate": "RELATES",
    "related": "RELATES",
    "relates": "RELATES",
    "connect": "CONNECTS",
    "connected": "CONNECTS",
    "connects": "CONNECTS",
    "link": "LINKS",
    "linked": "LINKS",
    "links": "LINKS",
    "imply": "IMPLIES",
    "implied": "IMPLIES",
    "implies": "IMPLIES",
    "encode": "ENCODES",
    "encoded": "ENCODES",
    "encodes": "ENCODES",
    "map": "MAPS_TO",
    "mapped": "MAPS_TO",
    "maps": "MAPS_TO",
    "derive": "DERIVES",
    "derived": "DERIVES",
    "derives": "DERIVES",
    "generate": "GENERATES",
    "generated": "GENERATES",
    "generates": "GENERATES",
    "constrain": "CONSTRAINS",
    "constrained": "CONSTRAINS",
    "constrains": "CONSTRAINS",
    "couple": "COUPLES",
    "coupled": "COUPLES",
    "couples": "COUPLES",
}
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")


def _authority() -> dict[str, bool]:
    return {
        "production_runtime_write": False,
        "execution_admitted": False,
        "canon_allowed": False,
    }


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _commit(domain: bytes, value: Any) -> str:
    return hashlib.blake2b(domain + _canonical(value), digest_size=32).hexdigest()


def _normalized_title(value: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in str(value)).split())


def _lexemes(value: str) -> list[str]:
    return [match.strip("_-") for match in _TOKEN_RE.findall(str(value).casefold())]


def _tokens(value: str) -> set[str]:
    out: set[str] = set()
    for token in _lexemes(value):
        if (
            len(token) < 4
            or token in _STOPWORDS
            or token in _RELATION_FORMS
            or token.isdigit()
        ):
            continue
        out.add(token)
    return out


def _relation_operators(value: str) -> set[str]:
    return {_RELATION_FORMS[token] for token in _lexemes(value) if token in _RELATION_FORMS}


def _source_id(row: Mapping[str, Any]) -> str:
    basis = {
        "provider": row.get("provider"),
        "doi": row.get("doi"),
        "url": row.get("url"),
        "title": row.get("title"),
    }
    return "SRC-" + _commit(b"GREMLIN-RESEARCH-SOURCE/v0.1\0", basis)[:16]


def _source_text(source: Mapping[str, Any]) -> str:
    return " ".join(
        value for value in (str(source.get("title") or ""), str(source.get("summary") or "")) if value
    )


def _content_commitment(source: Mapping[str, Any]) -> str:
    basis = {
        "content_basis": str(source.get("content_basis") or ""),
        "title": str(source.get("title") or ""),
        "summary": str(source.get("summary") or ""),
    }
    return _commit(b"GREMLIN-RESEARCH-CONTENT/v0.1\0", basis)


def _prepare_sources(rows: Iterable[Mapping[str, Any]], *, max_sources: int) -> list[dict[str, Any]]:
    limit = int(max_sources)
    if not (1 <= limit <= 50):
        raise ValueError("max_sources must be in 1..50")
    sources: list[dict[str, Any]] = []
    for raw in list(rows)[:limit]:
        row = dict(raw)
        source = {
            "source_id": _source_id(row),
            "provider": row.get("provider"),
            "title": str(row.get("title") or "").strip(),
            "url": row.get("url"),
            "doi": row.get("doi"),
            "authors": list(row.get("authors") or []),
            "published": row.get("published"),
            "updated": row.get("updated"),
            "container": row.get("container"),
            "summary": str(row.get("summary") or "").strip(),
            "content_basis": "TITLE_PLUS_AVAILABLE_METADATA_AND_ABSTRACT",
        }
        source["content_commitment"] = _content_commitment(source)
        source["content_length_chars"] = len(_source_text(source))
        sources.append(source)
    return sources


def _source_receipt(source: Mapping[str, Any]) -> dict[str, Any]:
    text = _source_text(source)
    core = {
        "source_id": source["source_id"],
        "content_basis": source["content_basis"],
        "content_commitment": source["content_commitment"],
        "content_length_chars": len(text),
        "evidence_text": text,
    }
    return {
        **core,
        "source_receipt_commitment": _commit(b"GREMLIN-RESEARCH-SOURCE-RECEIPT/v0.1\0", core),
    }


def _owl(context: Mapping[str, Any]) -> dict[str, Any]:
    sources = list(context["sources"])
    provider_counts = Counter(str(row.get("provider") or "unknown") for row in sources)
    dated = sum(bool(row.get("published")) for row in sources)
    abstracts = sum(bool(row.get("summary")) for row in sources)
    url_count = sum(bool(row.get("url")) for row in sources)
    return {
        "species": "OWL",
        "role": "epistemic audit",
        "epistemic_status": "CANDIDATE_AUDIT",
        "source_count": len(sources),
        "provider_counts": dict(sorted(provider_counts.items())),
        "sources_with_dates": dated,
        "sources_with_abstract_or_summary": abstracts,
        "sources_with_urls": url_count,
        "provider_errors": list(context.get("provider_errors") or []),
        "audit_flags": [
            "METADATA_LEVEL_EVIDENCE" if abstracts < len(sources) else "ABSTRACT_LEVEL_EVIDENCE_AVAILABLE",
            "PARTIAL_PROVIDER_FAILURE" if context.get("provider_errors") else "PROVIDERS_COMPLETED_WITHOUT_RECORDED_ERROR",
        ],
        "support_source_ids": [row["source_id"] for row in sources],
        "authority": _authority(),
    }


def _spider(context: Mapping[str, Any]) -> dict[str, Any]:
    sources = list(context["sources"])
    query_tokens = _tokens(str(context["query"]))
    coverage: dict[str, list[str]] = defaultdict(list)
    predicate_coverage: dict[str, list[str]] = defaultdict(list)
    source_tokens: dict[str, set[str]] = {}
    source_predicates: dict[str, set[str]] = {}

    for source in sources:
        sid = source["source_id"]
        text = _source_text(source)
        tokens = _tokens(text)
        predicates = _relation_operators(text)
        source_tokens[sid] = tokens
        source_predicates[sid] = predicates
        for token in sorted(tokens):
            coverage[token].append(sid)
        for predicate in sorted(predicates):
            predicate_coverage[predicate].append(sid)

    ranked = sorted(
        ((token, ids) for token, ids in coverage.items() if len(ids) >= 2 or token in query_tokens),
        key=lambda item: (-len(item[1]), item[0]),
    )[:16]
    concepts = [
        {"concept": token, "source_count": len(ids), "support_source_ids": ids[:12]}
        for token, ids in ranked
    ]
    relation_predicates = [
        {"operator": predicate, "source_count": len(ids), "support_source_ids": ids[:12]}
        for predicate, ids in sorted(predicate_coverage.items(), key=lambda item: (-len(item[1]), item[0]))
    ]

    edges: list[dict[str, Any]] = []
    concept_names = [row["concept"] for row in concepts[:10]]
    for index, left in enumerate(concept_names):
        for right in concept_names[index + 1 :]:
            ids = [
                source["source_id"]
                for source in sources
                if left in source_tokens[source["source_id"]] and right in source_tokens[source["source_id"]]
            ]
            if ids:
                predicates = sorted(
                    {
                        predicate
                        for sid in ids
                        for predicate in source_predicates.get(sid, set())
                    }
                )
                edges.append(
                    {
                        "left": left,
                        "right": right,
                        "cooccurrence_source_count": len(ids),
                        "support_source_ids": ids[:10],
                        "operator_candidates": predicates,
                        "directionality": "UNRESOLVED_FROM_TERM_LEVEL_EXTRACTION",
                    }
                )
    edges.sort(key=lambda row: (-row["cooccurrence_source_count"], row["left"], row["right"]))
    return {
        "species": "SPIDER",
        "role": "relation, dependency and isomorphism scan",
        "epistemic_status": "RELATION_CANDIDATES",
        "concepts": concepts,
        "relation_predicates": relation_predicates,
        "relation_edges": edges[:24],
        "relation_basis": "CONCEPT_COOCCURRENCE_PLUS_OBSERVED_RELATIONAL_VERBS_IN_TITLE_OR_AVAILABLE_ABSTRACT",
        "directionality_gate": "SENTENCE_OR_FULL_TEXT_PARSE_REQUIRED_FOR_SUBJECT_PREDICATE_OBJECT",
        "authority": _authority(),
    }


def _mole(context: Mapping[str, Any]) -> dict[str, Any]:
    spider = _spider(context)
    concepts = spider["concepts"]
    path = [row["concept"] for row in concepts[:5]]
    operators = [row["operator"] for row in spider.get("relation_predicates", [])[:8]]
    support: list[str] = []
    for row in concepts[:5]:
        for sid in row["support_source_ids"]:
            if sid not in support:
                support.append(sid)
    return {
        "species": "MOLE",
        "role": "deep local derivation",
        "epistemic_status": "STRUCTURAL_DERIVATION_CANDIDATE",
        "candidate_concept_path": path,
        "candidate_relation_operators": operators,
        "support_source_ids": support[:16],
        "equation_status": "UNRESOLVED_FROM_METADATA",
        "derivation_gate": "REQUIRES_FULL_TEXT_OR_EXPLICIT_PREMISES_FOR_EQUATION_LEVEL_PROMOTION",
        "directionality_gate": "REQUIRES_SUBJECT_PREDICATE_OBJECT_RESOLUTION",
        "authority": _authority(),
    }


def _hound(context: Mapping[str, Any]) -> dict[str, Any]:
    sources = list(context["sources"])
    title_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in sources:
        title = _normalized_title(source.get("title") or "")
        if title:
            title_groups[title].append(source)

    version_clusters: list[dict[str, Any]] = []
    for normalized, rows in title_groups.items():
        if len(rows) < 2:
            continue
        version_clusters.append(
            {
                "normalized_title": normalized,
                "source_ids": [row["source_id"] for row in rows],
                "urls": [row.get("url") for row in rows],
                "published": [row.get("published") for row in rows],
                "classification": "VERSION_OR_DUPLICATE_CLUSTER_NOT_ASSUMED_CONTRADICTION",
            }
        )

    missing_summary = [row["source_id"] for row in sources if not row.get("summary")]
    provider_errors = list(context.get("provider_errors") or [])
    return {
        "species": "HOUND",
        "role": "contradiction, anomaly and test-target scan",
        "epistemic_status": "ADVERSARIAL_AUDIT",
        "contradictions": [],
        "version_or_duplicate_clusters": version_clusters,
        "provider_errors": provider_errors,
        "test_targets": [
            {
                "target": "FULL_TEXT_CLAIM_COMPARISON",
                "reason": "metadata alone cannot establish semantic contradiction",
                "priority": "HIGH",
            },
            {
                "target": "SUBJECT_PREDICATE_OBJECT_PARSE",
                "reason": "observed relation verbs are meaningful but directionality requires sentence context",
                "priority": "HIGH",
            },
            {
                "target": "VERSION_DIFF_AUDIT",
                "reason": "same-title or version clusters should be compared before synthesis",
                "priority": "MEDIUM" if version_clusters else "LOW",
            },
        ],
        "limitations": {
            "sources_without_abstract_or_summary": missing_summary,
            "text_level_contradiction_test_completed": False,
            "directed_relation_parse_completed": False,
        },
        "authority": _authority(),
    }


def _generic_species(species: str, context: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "species": species,
        "epistemic_status": "REFERENCE_HANDLER_MINIMAL",
        "support_source_ids": [row["source_id"] for row in context["sources"]],
        "authority": _authority(),
    }


def _run_species(species: str, context: Mapping[str, Any]) -> dict[str, Any]:
    name = str(species).strip().upper()
    if name == "OWL":
        return _owl(context)
    if name == "SPIDER":
        return _spider(context)
    if name == "MOLE":
        return _mole(context)
    if name == "HOUND":
        return _hound(context)
    return _generic_species(name, context)


def _belzebub(bundle: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    candidates = list(bundle.get("specialist_candidates") or [])
    by_species: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in candidates:
        by_species[str(row.get("species") or "UNKNOWN")].append(row.get("candidate") or {})

    spider_candidates = by_species.get("SPIDER", [])
    mole_candidates = by_species.get("MOLE", [])
    hound_candidates = by_species.get("HOUND", [])
    owl_candidates = by_species.get("OWL", [])

    concepts: list[str] = []
    operators: list[str] = []
    for candidate in spider_candidates:
        for row in candidate.get("concepts", [])[:8]:
            concept = str(row.get("concept") or "")
            if concept and concept not in concepts:
                concepts.append(concept)
        for row in candidate.get("relation_predicates", [])[:8]:
            operator = str(row.get("operator") or "")
            if operator and operator not in operators:
                operators.append(operator)
    for candidate in mole_candidates:
        for concept in candidate.get("candidate_concept_path", [])[:5]:
            if concept and concept not in concepts:
                concepts.append(concept)
        for operator in candidate.get("candidate_relation_operators", [])[:8]:
            if operator and operator not in operators:
                operators.append(operator)

    version_clusters = sum(
        len(candidate.get("version_or_duplicate_clusters", [])) for candidate in hound_candidates
    )
    provider_errors = list(context.get("provider_errors") or [])
    source_ids = [row["source_id"] for row in context["sources"]]

    if concepts:
        bridge = " -> ".join(concepts[:5])
        operator_note = f" Observed relation operators: {', '.join(operators[:6])}." if operators else ""
        summary = (
            f"Candidate literature concept path extracted from the current evidence bundle: {bridge}."
            f"{operator_note} Operators are evidence-bearing relation candidates; directed subject-predicate-object "
            "assignment remains gated until sentence/full-text parsing."
        )
    else:
        bridge = None
        summary = (
            "The evidence bundle was collected and audited, but no stable multi-source concept path "
            "cleared the deterministic reference extractor."
        )

    return {
        "species": "BELZEBUB",
        "role": "defensive candidate synthesis",
        "epistemic_status": "CANDIDATE_SYNTHESIS",
        "answer": summary,
        "candidate_bridge": bridge,
        "observed_relation_operators": operators,
        "relation_directionality": "UNRESOLVED_PENDING_SENTENCE_OR_FULL_TEXT_PARSE",
        "source_count": len(source_ids),
        "support_source_ids": source_ids,
        "owl_audit_count": len(owl_candidates),
        "provider_errors": provider_errors,
        "version_or_duplicate_cluster_count": version_clusters,
        "contradiction_status": "TEXT_LEVEL_CHECK_REQUIRED",
        "equation_status": "UNRESOLVED_FROM_METADATA",
        "promotion_gate": "CANDIDATE_ONLY_PENDING_FULL_TEXT_AND_DOMAIN_VALIDATION",
        "authority": _authority(),
    }


def _submit_reference_species(
    broker: WorkerBroker,
    species: str,
    context: Mapping[str, Any],
) -> list[str]:
    name = str(species).strip().upper()
    worker_id = f"builtin-research-{name.lower()}"
    broker.register_worker(
        worker_id,
        [name],
        capabilities=["deterministic-reference-research-v0.1"],
        vector_width=8,
        max_batch=128,
    )
    completed: list[str] = []
    while True:
        lease = broker.claim(worker_id, species=name, limit=128)
        if not lease["lease_id"]:
            break
        results = []
        for task in lease["tasks"]:
            results.append(
                {
                    "task_id": task["task_id"],
                    "status": "CANDIDATE",
                    "output": _run_species(name, context),
                }
            )
            completed.append(task["task_id"])
        broker.submit(worker_id, lease["lease_id"], results)
    return completed


def execute_research(
    query: str,
    *,
    providers: Iterable[str] = ("crossref", "arxiv", "duckduckgo"),
    limit_per_provider: int = 6,
    max_species: int = 4,
    max_sources: int = 12,
) -> dict[str, Any]:
    q = str(query).strip()
    if not q:
        raise ValueError("query must be non-empty")

    acquisition = research(
        q,
        providers=providers,
        limit_per_provider=limit_per_provider,
        max_species=max_species,
    )
    evidence = acquisition["evidence"]
    sources = _prepare_sources(evidence.get("results", []), max_sources=max_sources)
    if not sources:
        core = {
            "schema": EXECUTOR_SCHEMA,
            "version": EXECUTOR_VERSION,
            "query": q,
            "status": "NO_EVIDENCE_FAIL_CLOSED",
            "acquisition": acquisition,
            "stage_executions": [],
            "synthesis": None,
            "citations": [],
            "source_receipts": [],
            "authority": _authority(),
        }
        core["execution_commitment"] = _commit(b"GREMLIN-RESEARCH-EXECUTION/v0.1\0", core)
        return core

    context = {
        "query": q,
        "sources": sources,
        "evidence_commitment": evidence.get("evidence_commitment"),
        "provider_errors": evidence.get("provider_errors", []),
    }
    broker = WorkerBroker()
    task_ids: list[str] = []
    stage_executions: list[dict[str, Any]] = []
    plan = acquisition["research_plan"]
    plan_key = str(plan.get("plan_commitment") or acquisition.get("research_commitment") or "research")[:16]

    for index, stage in enumerate(plan.get("stages", [])):
        roles = list(stage.get("route_mask") or [])
        if not roles:
            stage_executions.append(
                {
                    "stage_id": stage.get("stage_id"),
                    "status": "NO_CONFIDENT_ROUTE_NOT_EXECUTED",
                    "route_mask": [],
                    "task_ids": [],
                }
            )
            continue
        request_id = f"research-{plan_key}-{index:02d}"
        queued = fanout(
            broker,
            {
                "stage_id": stage.get("stage_id"),
                "query": q,
                "evidence_commitment": evidence.get("evidence_commitment"),
                "source_ids": [row["source_id"] for row in sources],
            },
            roles,
            request_id=request_id,
            route_context={
                "route_commitment": stage.get("route_commitment"),
                "stage_id": stage.get("stage_id"),
            },
        )
        stage_task_ids = [row["task_id"] for row in queued["tasks"]]
        for role in roles:
            _submit_reference_species(broker, role, context)
        collected = collect(broker, stage_task_ids)
        if not collected["complete"]:
            raise RuntimeError(f"reference execution did not complete stage {stage.get('stage_id')}")
        task_ids.extend(stage_task_ids)
        stage_executions.append(
            {
                "stage_id": stage.get("stage_id"),
                "status": "CANDIDATE_STAGE_COMPLETE",
                "route_mask": roles,
                "route_commitment": stage.get("route_commitment"),
                "task_ids": stage_task_ids,
                "results": [
                    {
                        "species": row["species"],
                        "task_id": row["task_id"],
                        "task_commitment": row["task_commitment"],
                        "result_commitment": row["result_commitment"],
                        "candidate": row["result"],
                    }
                    for row in collected["tasks"]
                ],
            }
        )

    synthesis_result = None
    if task_ids:
        synthesis = enqueue_synthesis(
            broker,
            task_ids,
            request_id=f"research-{plan_key}-synthesis",
        )
        worker_id = "builtin-research-belzebub"
        broker.register_worker(
            worker_id,
            ["BELZEBUB"],
            capabilities=["deterministic-reference-synthesis-v0.1"],
            vector_width=8,
            max_batch=8,
        )
        lease = broker.claim(worker_id, species="BELZEBUB", limit=8)
        if not lease["lease_id"] or len(lease["tasks"]) != 1:
            raise RuntimeError("BELZEBUB reference synthesis lease was not created")
        task = lease["tasks"][0]
        output = _belzebub(task["payload"], context)
        broker.submit(
            worker_id,
            lease["lease_id"],
            [{"task_id": task["task_id"], "status": "CANDIDATE", "output": output}],
        )
        synthesis_result = broker.task_result(synthesis["task_id"])

    citations = [
        {
            "source_id": row["source_id"],
            "provider": row.get("provider"),
            "title": row.get("title"),
            "url": row.get("url"),
            "doi": row.get("doi"),
            "published": row.get("published"),
            "content_basis": row.get("content_basis"),
            "content_commitment": row.get("content_commitment"),
        }
        for row in sources
    ]
    source_receipts = [_source_receipt(row) for row in sources]
    core = {
        "schema": EXECUTOR_SCHEMA,
        "version": EXECUTOR_VERSION,
        "mode": "BUILTIN_REFERENCE_BESTIARY_EXECUTOR",
        "query": q,
        "status": "CANDIDATE_SYNTHESIS_READY" if synthesis_result else "CANDIDATE_STAGES_COMPLETE",
        "acquisition": acquisition,
        "stage_executions": stage_executions,
        "synthesis": synthesis_result,
        "citations": citations,
        "source_receipts": source_receipts,
        "worker_abi_exercised": True,
        "authority": _authority(),
    }
    core["execution_commitment"] = _commit(b"GREMLIN-RESEARCH-EXECUTION/v0.1\0", core)
    return core