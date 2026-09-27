# GREMLIN Residual-Preserving Spectroscopy v0.1

Status: CANDIDATE / IMPLEMENTED / INTERPRETATION_LAST / NO_CANON_PROMOTION

Residual is not a synonym for disposable noise.

For every acquisition

[
x = \hat x + r
]

the raw observation (x), model (\hat x), and residual (r) are independently committed and preserved. Analysis may use detrended/windowed copies, but the source residual is never destructively overwritten.

Allowed diagnostic classes:

- STOCHASTIC_BACKGROUND_COMPATIBLE
- SYSTEMATIC_OR_INSTRUMENTAL_CANDIDATE
- SYSTEMATIC_DRIFT_CANDIDATE
- KNOWN_MODEL_STRUCTURE_CANDIDATE
- UNRESOLVED_STRUCTURED_CANDIDATE
- UNRESOLVED_RESIDUAL

These are diagnostic classes, not ontological claims.

v0.1 measures cross-run spectral persistence, phase coherence, spectral concentration, lag structure, drift, multi-scale block-mean scaling, nuisance correlation and known-template correlation.

The global stack rule is

[
\boxed{
RAW
\to MODEL
\to RESIDUAL\ PRESERVED
\to STRUCTURE\ TESTS
\to CONTROL\ ATTRIBUTION
\to INTERPRETATION\ LAST.
}
]

A structured residual cannot be promoted to new physics, a new physical carrier, or time fluctuations at this layer. Instrument/environment/clock, sampling/jitter/alias, known-physics and independent-replication controls are required first.

The intended consumers are GREMLIN spectroscopic holonomy, PhaseNav spectroscopy/telescope/microscope lanes and Resonant-Chemistry spectroscopy.
