# GREMLIN Joint Quantum Witness v1.0

Status: IMPLEMENTED CANDIDATE — CI verdict required.

## Purpose

This layer extends the relational Lambda / connection-path / QHTRI lineage with an explicit joint-state witness. It separates phase synchronization from quantum-state nonseparability and provides a deterministic research receipt for a declared two-body coupling evolution.

The lineage is

```text
Lambda_R
-> effective relational source energy
-> geometry / connection commitment
-> closed-path connection integral
-> tau_holonomy
-> QHTRI epsilon
-> joint pure state
-> concurrence witness
-> declared relational coupling evolution
```

The v1.0 implementation preserves the existing v0.9 provenance constraint:

```text
tau_origin = CONNECTION_PATH_INTEGRAL
```

## Joint pure state

For the ordered basis

```text
|00>, |01>, |10>, |11>
```

the state is

```math
|\Psi\rangle = a_{00}|00\rangle + a_{01}|01\rangle + a_{10}|10\rangle + a_{11}|11\rangle.
```

Input amplitudes are deterministically normalized:

```math
|\Psi\rangle = \frac{|\Psi_{raw}\rangle}{\sqrt{\sum_k |a_k|^2}}.
```

The state receipt binds the QHTRI connection-derived commitment, so the joint-state layer retains the geometric phase-lag lineage.

## Pure two-qubit entanglement witness

For a normalized pure two-qubit state the implementation computes concurrence

```math
C_{ent}=2\left|a_{00}a_{11}-a_{01}a_{10}\right|.
```

The associated single-qubit reduced purity is

```math
\mathrm{Tr}(\rho_A^2)=1-\frac{C_{ent}^2}{2}.
```

A declared numerical tolerance is carried in the receipt. The classification is:

```text
C_ent <= tolerance  -> SEPARABLE_WITHIN_TOLERANCE
C_ent >  tolerance  -> ENTANGLED_PURE_STATE_WITNESS
```

The witness explicitly records

```text
synchronization_entanglement_equivalence = false
```

because QHTRI/Kuramoto phase locking and quantum-state nonseparability are distinct observables.

A regression test binds this distinction directly: a QHTRI state with exact phase lock can coexist with a product joint state whose concurrence is zero.

## Declared relational coupling evolution

v1.0 adds a model-level two-body interaction

```math
H_{rel}=J_{rel}(\sigma_z\otimes\sigma_z).
```

For duration `dt`,

```math
U_{rel}=\exp\left(-\frac{i}{\hbar}H_{rel}\,dt\right),
```

with

```math
\chi=\frac{J_{rel}dt}{\hbar}.
```

In the computational basis this yields the diagonal phase action

```text
|00> -> exp(-i chi)|00>
|01> -> exp(+i chi)|01>
|10> -> exp(+i chi)|10>
|11> -> exp(-i chi)|11>
```

The implementation recomputes the final amplitudes and concurrence during validation.

A model witness is reported when a state with initial concurrence within tolerance evolves to final concurrence above tolerance:

```text
ENTANGLEMENT_GENERATED_BY_DECLARED_ZZ_COUPLING_WITHIN_MODEL
```

The attribution scope is recorded as

```text
DECLARED_ZZ_MODEL_ONLY
```

## Coupling-energy frontier

The relational coupling energy `J_rel` is bound to an explicit source reference and source commitment.

The current receipt records

```text
coupling_energy_scale_origin = EXPLICIT_UPSTREAM_OR_MODEL_ADAPTER
lambda_holonomy_to_J_rel_derivation_status = OPEN
```

Therefore the next derivation target is an explicit law connecting the relational Lambda / geometry / holonomy state to the coupling-energy scale.

The natural target interface is

```math
J_{rel}=\mathcal J(\Lambda_R,\mathcal H,\mathcal O,\ldots),
```

where every additional argument must have a declared physical dimension, normalization and provenance. No implicit rescaling is admitted.

## Validation targets

The v1.0 test suite checks:

- product-state concurrence equals zero;
- Bell-state concurrence equals one;
- exact QHTRI phase lock can coexist with zero concurrence;
- deterministic joint-state normalization;
- zero-norm rejection;
- state and witness tamper rejection;
- declared ZZ evolution from a product state to maximal concurrence at the appropriate coupling phase;
- zero-coupling control remains separable;
- evolved-amplitude tamper rejection;
- QHTRI connection-derived lineage survives into the joint state and coupling receipt.

## Epistemic boundary

The joint-state and coupling layers are research bindings with candidate status. A concurrence witness establishes nonseparability of the represented pure two-qubit state. Attribution of that state to a physical neutrino-pair preparation requires a corresponding state-preparation / measurement witness. Attribution of the coupling energy to the relational Lambda field requires the pending `Lambda_R -> J_rel` derivation.
