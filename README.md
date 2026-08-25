# GREMLIN

GREMLIN is the root system. OCTOPUS and BELZEBUB are writable subordinate tools with independent local `CURRENT` heads, while GREMLIN binds verified tool heads into one aggregate `SUPER_CURRENT`.

## Native authority

Authoritative runtime declarations live in `native/*.pnv` and use the existing PhaseNav Natural Coding operator vocabulary. Python is retained only as a reference/test harness.

```text
GREMLIN
├── SUPER_CURRENT
├── Triple Pulse Boot: IDENTITY -> DOMAIN -> AUTHORITY
├── REQUEST -> COUPLING -> ADMISSION
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

Boot protocol:

1. `IDENTITY` pulse — verify current identity.
2. `DOMAIN` pulse — verify current live runtime generation.
3. `AUTHORITY` pulse — verify admission authority.
4. `REQUEST`.
5. `COUPLING` to the current live generation.
6. `ADMISSION` only after 3/3 pulse receipts bind the same generation.

Native witness: `native/GREMLIN_TRIPLE_PULSE_BOOT_V0_5.pnv`.

Motto: `Verbis utor, informationem in existentiam converto.`

BELZEBUB quarantines untrusted code as data, performs semantic defensive analysis, and emits repair/immunity candidates. Quarantined content has no execution authority.
