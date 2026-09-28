# GREMLIN PBH Relational Tidal Gate v0.1

This gate is deliberately upstream of any PBH identity claim.

A sufficiently distant unseen body acts, to leading order over a short planetary ranging baseline, through the trace-free tidal tensor

```math
T = mu (3 u u^T - I),   mu = G M / r^3.
```

The relational object is therefore a **common tensor recovered independently from different orbital data layers**.

Required layers:

1. major-planet ranging / ephemeris residuals;
2. Pluto + large-TNO astrometric residuals;
3. detached-TNO secular response as a degeneracy breaker.

The gate compares:

- sign-degenerate source axes;
- tensor shape;
- fitted tidal amplitude `mu`;
- provenance independence.

A gravitational fit cannot distinguish a PBH from an ordinary dark planet of the same mass and trajectory. Therefore the output remains `RELATIONAL_SOURCE_CANDIDATE`; PBH identity requires a non-size-dependent discriminator such as lensing or another compactness-sensitive observable.
