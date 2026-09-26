# GREMLIN FERRET Astro-Data Source Profile v0.1

Status: `CANDIDATE / FAIL-CLOSED / READ-ONLY ACQUISITION`

This profile extends FERRET without weakening its existing external-actuation boundary.

FERRET may prepare and provenance-track official astronomical data sources, but it does not interpret the scientific result and it does not autonomously fan out workers. The handoff is explicit:

```text
official source
  -> FERRET source validation
  -> FITS provenance receipt
  -> HUMMINGBIRD capture
  -> BAT / HOUND / OWL / SPIDER analysis
  -> BELZEBUB defensive synthesis
  -> GREMLIN aggregate candidate
```

## Source constraints

Allowlisted official source hosts in v0.1:

- `irsa.ipac.caltech.edu`
- `lambda.gsfc.nasa.gov`
- `skyview.gsfc.nasa.gov`

HTTPS only. No credentials. No form submission. No external mutation. A source outside the allowlist is rejected rather than silently substituted.

## FITS source classes

- `CMB_COMPONENT`
- `CMB_FREQUENCY`
- `FOREGROUND_CONTROL`
- `XRAY_CONTROL`
- `POWER_SPECTRUM`

A source receipt binds the product, target coordinates, query parameters, expected file name and official URL. A FITS provenance receipt may additionally bind byte count, SHA-256 and selected FITS header cards.

## PBH/CMB analysis contract

For a pre-registered target coordinate, the recommended Bestiary route is:

- BAT — Fourier/phase/harmonic markers and cross-map phase consistency;
- HOUND — anomaly, mismatch and false-positive controls;
- OWL — provenance and epistemic classification;
- SPIDER — cross-source relation graph and foreground dependencies;
- BELZEBUB — adversarial synthesis and overclaim rejection;
- GREMLIN — aggregate candidate with live PhaseNav/T^36 context when available.

FERRET does not promote any marker to a physical PBH detection.

## Authority

```text
external_mutation_allowed = false
ferret_worker_fanout = false
routing_authority = OCTOPUS_OR_EXPLICIT_HOST_ONLY
canon_allowed = false
```
