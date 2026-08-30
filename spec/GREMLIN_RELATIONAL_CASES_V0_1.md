# GREMLIN Relational Cases v0.1

Status: **CANDIDATE / reference implementation**  
Scope: deterministic Polish relation typing for GREMLIN Research Engine  
Authority: `production_runtime_write=false`, `execution_admitted=false`, `canon_allowed=false`

## Core model

GREMLIN represents a parsed relation as an operator with typed grammatical ports:

```text
R = OP[CASE:operator_role=entity, ...]
```

Grammatical case and semantic role are distinct. A case constrains the relational port; the operator determines the local role carried by that port.

For example, instrumental (`INS`) can participate in several operators without collapsing their meanings:

```text
NAMES[NOM:namer=@speaker, ACC:entity_named=cię, INS:assigned_name_or_designation=Zosią]
SPEAKS_ABOUT[NOM:speaker=@speaker, LOC:topic=geometrii, INS:interlocutor=Zosią]
CONNECTED_WITH[NOM:entity=Zosia, INS:counterpart_in_relation=Adrianem]
```

The operator is the relation. Its arguments are entities bound through case-typed ports.

## Case alphabet

| Port | Polish case | Question | General relational capacity |
|---|---|---|---|
| `NOM` | mianownik | kto? co? | source / subject |
| `GEN` | dopełniacz | kogo? czego? | origin / possession / partitive / governed relation |
| `DAT` | celownik | komu? czemu? | recipient / target / orientation |
| `ACC` | biernik | kogo? co? | object / patient |
| `INS` | narzędnik | z kim? z czym? / kim? czym? | coupling / companion / predicative / instrumental relation |
| `LOC` | miejscownik | o kim? o czym? / w kim? w czym? | topic / context / location |
| `VOC` | wołacz | address | addressee / activation |

These capacities are not one-to-one semantic definitions. Operator-local role remains authoritative inside the candidate frame.

## Reference operator signatures

```text
NAMES          : NOM × ACC × INS
DESCRIBES      : NOM × ACC × [INS] × [LOC]
SPEAKS_ABOUT   : NOM × LOC × [INS]
CONNECTED_WITH : NOM × INS
BELONGS_TO     : NOM × GEN
GIVES          : NOM × DAT × ACC
ADDRESSES      : NOM × VOC
```

Square brackets mark optional ports.

## Evidence and commitments

Every relation frame contains:

- the operator,
- required and optional signature,
- case binding,
- case name and question,
- entity surface form,
- operator-local role,
- evidence tag,
- confidence,
- explicit missing required ports,
- completeness flag,
- BLAKE2b-256 relation commitment,
- candidate-only authority state.

The parser fails closed on unknown cases, unadmitted ports, duplicate case bindings and missing entities. Missing required ports remain explicit rather than being silently inferred.

## Bestiary integration

`gremlin_research_relational` first executes the existing Internet research pipeline and then propagates the case frame through the Bestiary:

```text
relation text
   ↓
RELATIONAL CASE PARSER
   ↓
SPIDER  — case-typed relation graph
MOLE    — relational constraints on candidate derivation
HOUND   — frame/claim audit target
   ↓
BELZEBUB — candidate synthesis retaining the typed relation
```

This augments source-derived term co-occurrence and relation predicates. A grammar-bound frame may orient the arguments of a relation supplied by the query or caller; validation against source claims remains a separate evidence step.

## Live validation receipt

Validated on branch `feat/gremlin-research-engine-v0.1` at head `e5385d90d61b97ab80fe0b90ccb509f622de152b`.

Case suite:

- 12/12 relational-case unit tests PASS,
- 7/7 reference sentences PASS,
- full `NOM/GEN/DAT/ACC/INS/LOC/VOC` coverage PASS.

Full MCP contract:

- 40/40 tests PASS.

Live Internet relational probe:

```text
search query:
  audit evidence contradictions dependencies graph derive relation between
  Shannon entropy information geometry and quantum gravity

relation text:
  Informacja jest związana z geometrią.

parsed frame:
  CONNECTED_WITH[NOM:entity=Informacja, INS:counterpart_in_relation=geometrią]
```

The live run collected 10 sources from Crossref and arXiv with no recorded provider errors. The typed frame reached SPIDER, MOLE, HOUND and BELZEBUB. All live probe checks passed.

Live relational execution commitment:

```text
eabc9e950e0585237e4f412bf4d50dccfef76f68f5fa37d10f69fdb3abd1e6a8
```

Base research execution commitment:

```text
0facc24db2efa0a1bc56c093872f4609aa5513102dd9a8ac87d830b00a2df612
```

## Current parser scope

The current parser is a bounded deterministic Polish reference grammar. It validates the relational architecture and explicit case-port ABI. Expansion to full morphology, dependency parsing, anaphora/coreference and sentence-level source-claim extraction belongs to subsequent versions while preserving the same typed-port representation.
