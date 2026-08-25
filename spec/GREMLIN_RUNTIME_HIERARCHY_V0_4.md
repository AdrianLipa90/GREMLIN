# GREMLIN Runtime Hierarchy v0.4

Status: NATIVE_PNV_CANDIDATE

```text
GREMLIN (root system)
├── SUPER_CURRENT
├── Natural Queue / scalar tau
├── OCTOPUS (writable tool)
│   └── CURRENT
└── BELZEBUB (writable defensive tool)
    └── CURRENT
```

## Persistent memory

Each writable tool owns one local content-addressed namespace and one authoritative `CURRENT` pointer. A tool commit is `OBJECT -> RECEIPT -> CURRENT`. GREMLIN owns one aggregate `SUPER_CURRENT` and advances it only after both referenced tool heads verify. Tool writes do not overwrite each other and last-writer-wins is not admitted.

The operational surface is `/dev/shm/ciel_noema`. Persistent Library artifacts may hydrate or verify the live surface; they are not the operating state.

## Native execution

The authoritative runtime declarations are the `.pnv` files under `native/`. Python code is reference/test harness only. Natural continuation uses the existing PNCS operator sequence `ORDER -> TRANSFORM -> COMPOSITION`; no new PNV opcode is introduced.

## BELZEBUB boundary

BELZEBUB treats quarantined code as data. Quarantine has no execution authority. Its write scope is its own namespace and an immunity update requires a verified test receipt before its local `CURRENT` may advance.
