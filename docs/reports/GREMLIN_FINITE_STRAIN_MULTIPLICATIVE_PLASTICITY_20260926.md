# GREMLIN Finite-Strain Multiplicative Plasticity Audit
Date: 2026-09-26
Status: PASS / GL_PLUS_3_MULTIPLICATIVE_DYNAMICS

The continuum stack has been lifted from additive small-strain plastic
distortion to multiplicative finite-strain kinematics:

    F=F_eF_p.

The elastic energy remains objective and is evaluated on F_e.

Mandel-driven flow:

    L_p=m_dev dev M + m_vol mean(M)I

gives the exact fixed-total-F dissipation identity

    dot(psi)=-M:L_p<=0.

The state update

    F_p <- exp(dt L_p)F_p

keeps the plastic state in GL+(3); isochoric mobility preserves det F_p.

Independent crosschecks include:
- energy derivative vs dissipation;
- total Piola stress vs finite differences;
- matrix exponential vs scipy reference;
- determinant exponential identity;
- objectivity and rigid-rotation controls.

All checked invariants PASS.

Next controlled extension:
GL(4)/coframe kinematics through Lambda^2, with the unavoidable Z2 kernel
A and -A explicitly retained rather than hidden.
