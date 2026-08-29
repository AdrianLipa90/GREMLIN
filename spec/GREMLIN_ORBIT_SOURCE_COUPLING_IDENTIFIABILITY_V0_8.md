# GREMLIN Orbit Source/Coupling Identifiability v0.8

Status: CANDIDATE_ONLY / CHYBA

## Scope

This gate formalizes what the role-typed orbital kernel can identify from circular-orbit observables before an independent source or coupling calibration is supplied.

The scheduler kernel is

`omega^2 = (mu_source / r^3) * eta_G`

with

`eta_G = q_coupling / m_inertial`.

Therefore the observable invariant is

`K_orb = omega^2 * r^3 = mu_source * eta_G`.

## Identifiability theorem

For every `lambda > 0`, the transformation

`mu_source' = lambda * mu_source`

`eta_G' = eta_G / lambda`

preserves `K_orb` and therefore preserves `omega` at fixed `r`.

Consequently circular-orbit observations identify the product `K_orb`; they do not independently identify `mu_source` and `eta_G` without an additional source/coupling receipt.

## Admission rule

`resolve_factorization()` fails closed when neither factor is independently supplied.

If `mu_source` is supplied with an explicit `mu_source_profile_id`, then

`eta_G = K_orb / mu_source`.

If `eta_G` is supplied with an explicit `eta_g_profile_id`, then

`mu_source = K_orb / eta_G`.

If both are supplied, their product must match `K_orb` within the declared numeric tolerance.

No compatibility profile silently inserts `eta_G = 1`.

## RFC extensive-source adapter

The finite-cell extensive source candidate is

`E_Sigma = sum_a V_a * rho_G,a`.

A scheduler source-strength candidate requires an independently sourced coefficient:

`mu_source = C_mu * E_Sigma`.

The coefficient `C_mu` is explicit and remains a source/provenance gate for v0.9.

## Validation targets

T0 theorem/unit:
- exact `K_orb` round-trip;
- positive rescaling invariance;
- unique reconstruction when one factor is supplied;
- invalid-domain rejection.

T1 repository conformance:
- unsourced factorization returns `FAIL_UNSOURCED_FACTORIZATION`;
- source identifiers are mandatory for supplied factors;
- inconsistent double-supplied factors fail closed;
- no implicit `eta_G=1` path exists.

T2 exact provenance replay:
- pin implementation/test head and deterministic parameters in provenance.

T3 live NOEMA:
- required only for the live receipt layer; 36D execution remains on `/dev/shm/ciel_noema`.

## Definition of done

`PASS_EXACT_IDENTIFIABILITY` requires:
1. `K_orb` round-trips from `(omega, r)`;
2. all tested positive rescalings preserve the observable product;
3. independent `mu_source` reconstructs `eta_G` uniquely;
4. independent `eta_G` reconstructs `mu_source` uniquely;
5. neither factor is silently invented when both are unsourced;
6. RFC extensive-source conversion remains explicit through `C_mu`.
