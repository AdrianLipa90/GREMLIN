# GREMLIN Quantum Application Orchestrator v0.1

Status: `CANDIDATE / PHASENAV_NATIVE / PNCS_BOUND / NO_EARLY_COLLAPSE / LOCAL_FIRST`

## Upstream contracts

- `PNCS_QUANTUM_APPLICATION_RUNTIME_V0_31`
- `PHASENAV_QUANTUM_APPLICATION_STATE_V0_1`

## Purpose

GREMLIN is promoted from a flat job/status orchestrator model to an orchestrator of typed PhaseNav application states.

The scheduling object is

$
\Psi_J=(\Phi_{36},\mathcal A,\mathcal T,s,\tau,\Sigma,\mathcal P).
$

GREMLIN may inspect and transform these fields according to role authority, but it must not replace the internal state with PASS/FAIL or ready/not-ready before an explicit measurement boundary.

## Bestiary residual tensor

Bestiary analysis should preserve a typed residual structure

$
E_{ij}^{(k)}
$

where \(i,j\) identify related graph nodes and \(k\) identifies relation class, including logical, algebraic, provenance, dimensional, phase and empirical channels.

A residual is information. It is not automatically an error bit.

## Scheduler

The Geometry/Phase/State Scheduler remains valid. Its continuous fields are primary:

- phase36;
- readiness;
- temperature;
- urgency;
- noise;
- residual/coherence fields when available.

The legacy `ready: bool` field is now explicitly a lease-admission measurement:

$
ready=\mathcal M_{lease}(\Psi_J)\in\{0,1\}.
$

It is not the underlying readiness state.

## Measurement boundaries

GREMLIN must name every classical projection. Initial required boundaries are:

- `M_lease`: worker lease eligibility;
- `M_safety`: fail-closed constitutional/safety admission;
- `M_release`: RELEASE/QUARANTINE;
- `M_effect`: external actuation authorization.

All pre-measurement state and provenance must survive in the receipt.

## Local-first fabric

GREMLIN schedules capabilities, not servers.

$
C_j=(\Phi_j^{cap},CPU,GPU,RAM,toolchain,trust,latency).
$

Railway, GitHub Actions, Docker and remote services are not architectural dependencies. If used, they are optional external adapters.

Primary path:

$
\boxed{GREMLIN\rightarrow PNCS\rightarrow PhaseNav\rightarrow local\ execution\ cells}
$

## Backend claim firewall

GREMLIN may call this a quantum application architecture because the state and measurement contracts are quantum-style. It must not report physical quantum execution unless the receipt backend is `QPU_PHYSICAL`.

## Authority

This v0.1 contract does not grant new external effects, canon promotion, repository mutation or FERRET authority. Existing fail-closed constitutional boundaries remain binding.
