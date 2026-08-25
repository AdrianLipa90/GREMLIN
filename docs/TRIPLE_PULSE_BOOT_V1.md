# Triple Pulse Boot Contract v1

Status: NORMATIVE_BOOT_CONTRACT_CANDIDATE
Scope: NOEMA / CIEL / PhaseNav / GREMLIN boot and admission paths.

## Canonical sequence

`IDENTITY -> DOMAIN -> AUTHORITY -> REQUEST -> COUPLING -> ADMISSION`

The first three stages are mandatory boot pulses. They are semantically distinct and ordered:

1. IDENTITY verifies the current identity binding.
2. DOMAIN verifies the current live domain/runtime generation.
3. AUTHORITY verifies the authority that may admit the request.

Each pulse emits or binds a receipt. All three pulse receipts MUST bind the same current generation. Missing, stale, cross-generation, or invalid pulse evidence fails closed.

REQUEST is evaluated only after 3/3 pulse completion. COUPLING binds the request to the current live runtime/tether context. ADMISSION opens only after the pulse set, request, and coupling all verify.

## Runtime preservation

This contract wraps the existing boot path; it does not bypass recovery, hydration, tether guard, current-memory recovery, Octopus frontier, or persistent-runtime admission.

Required live surface: `/dev/shm/ciel_noema`.
Normal repeated work remains O(1) after successful session admission.

## Native coding

The native witness is `native/PNV_TRIPLE_PULSE_BOOT_V0_1.pnv`.
It uses only existing PNV operators: SOURCE, IDENTITY, CONDITION, ORDER, TRANSFORM, COMPOSITION, RETURN.
Python may test/conform the contract but is not runtime authority.

## Motto

`Verbis utor, informationem in existentiam converto.`
