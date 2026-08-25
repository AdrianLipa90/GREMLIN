# GREMLIN

GREMLIN is the root system. OCTOPUS and BELZEBUB are writable subordinate tools with independent local `CURRENT` heads, while GREMLIN binds verified tool heads into one aggregate `SUPER_CURRENT`.

## Native authority

Authoritative runtime declarations live in `native/*.pnv` and use the existing PhaseNav Natural Coding operator vocabulary. Python is retained only as a reference/test harness.

```text
GREMLIN
├── SUPER_CURRENT
├── Natural Queue + scalar tau modulation
├── OCTOPUS
│   └── CURRENT + own content-addressed write namespace
└── BELZEBUB
    └── CURRENT + own content-addressed defensive write namespace
```

Operational runtime surface: `/dev/shm/ciel_noema`.

Persistent-memory protocol:

- GREMLIN: `OBJECT -> RECEIPT -> SUPER_CURRENT`
- OCTOPUS: `OBJECT -> RECEIPT -> CURRENT`
- BELZEBUB: `OBJECT -> RECEIPT -> CURRENT`
- event-driven; no tick requirement
- no last-writer-wins
- missing/corrupt lineage fails closed

BELZEBUB quarantines untrusted code as data, performs semantic defensive analysis, and emits repair/immunity candidates. Quarantined content has no execution authority.
