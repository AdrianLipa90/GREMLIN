# GREMLIN Residual-Preserving Spectroscopy v0.2

Status: CANDIDATE / IMPLEMENTED / 7-OF-7 LOCAL PASS / NO CANON PROMOTION

v0.2 strengthens the rule that residual is preserved rather than discarded.

New gates:
- median stacked residual spectrum across independent runs;
- weak persistent-line recovery even when single-run peak selection is unreliable;
- persistent micro-offset detection;
- cross-channel spectral coherence;
- multi-scale block-mean slope retained as a diagnostic coordinate.

A weak line may therefore become visible only after repeated acquisitions without altering or zeroing any source residual.

Diagnostic classes remain non-ontological. In particular,
UNRESOLVED_STRUCTURED_CANDIDATE does not mean new physics, and
PERSISTENT_OFFSET_CANDIDATE does not decide between calibration bias,
intermediate structure, environmental coupling or another mechanism.

Physical promotion requires independent instrument/environment/clock,
sampling/jitter/alias, known-physics and replication controls.

Global rule:

RAW -> MODEL -> RESIDUAL PRESERVED -> STACK/CROSS-CHANNEL STRUCTURE -> CONTROLS -> INTERPRETATION LAST.
