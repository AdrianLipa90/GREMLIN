# GREMLIN Radial Medium Identifiability v0.1

Status: `CANDIDATE_ONLY / EXACT_CENTRAL_IDENTITIES / SOURCE_ATTRIBUTION_FAIL_CLOSED`

This gate extends the existing role-typed orbital and holonomy work without promoting a physical condensate or information-potential source. GREMLIN receives a diagnostic layer for distinguishing a pure (1/r) radial kernel from a general stationary central effective scalar.

## Parent surfaces

- GREMLIN orbital source/coupling identifiability v0.8:
  (K_{m orb}=r^3Omega^2=mu_Seta_G) only for the declared pure (1/r) branch.
- GREMLIN connection-path holonomy v0.9:
  (	au) is a project holonomy coordinate; physical condensate-flux identification remains open.
- IDT 02JP/02JQ:
  nonlinear Madelung/BEC bridge and exact central inverse identities.
- RFC RF-L3:
  (U_I=(alpha_I/kappa_E)Xi_I), with physical calibration inherited and open.

## 1. Observed radial kernel

For any circular branch define

[
K_{m obs}(r)=r^3Omega^2(r).
]

The pure Kepler/source model is the special case

[
K_{m obs}(r)=mu_Seta_G=	ext{constant}.
]

For a general stationary central scalar (Phi_{m eff}),

[
Omega^2=rac{Phi_{m eff}'}{r},
qquad
kappa_{m epi}^2=4Omega^2+rrac{dOmega^2}{dr}.
]

Hence

[
oxed{
rac{dK_{m obs}}{dr}
=
r^2(kappa_{m epi}^2-Omega^2).
}
]

GREMLIN therefore treats nonzero (K_{m obs}') as evidence for non-Kepler radial structure, not as a source label.

## 2. BELZEBUB central-consistency residual

Define

[
oxed{
mathcal B(r)
=
kappa_{m meas}^2
-
4Omega_{m meas}^2
-
rrac{dOmega_{m meas}^2}{dr}.
}
]

A significant nonzero residual means the declared one-scalar stationary central model is inconsistent with the measurements. GREMLIN must not repair this by silently inserting a new source term.

## 3. Kepler-camouflage firewall

Any additional radial scalar of the form

[
deltaPhi(r)=C_0+rac{C_1}{r}
]

is exactly degenerate with a redefinition of the pure Kepler kernel under (Omega(r)) and (kappa_{m epi}(r)).

Therefore

[
oxed{
	ext{Kepler-shaped data}
otRightarrow
	ext{unique source/coupling identification}.
}
]

The v0.8 source/coupling non-identifiability theorem is thus strengthened in medium: even an apparently constant (K_{m obs}) does not establish that the full (1/r) coefficient is (mu_Seta_G).

## 4. Condensate-subtracted residual

If independent channels provide the density profile and the declared mean-field/quantum-pressure calibration, define

[
Q_ho=
rac{
abla^2sqrtho}{sqrtho}
]

and

[
oxed{
G_{m res}(r)
=
rOmega^2
-
rac{K_{m orb}}{r^2}
-
2mathcal M gho'
+
2mathcal M^2 Q_ho'.
}
]

Only after those independently constrained contributions are removed may GREMLIN route the residual to candidate source families. Under the conditional RFC + GREMLIN bridge,

[
rac{G_{m res}}{2mathcal M}
=
c_IXi_I'
-
J'cosepsilon
+
Jsinepsilon,epsilon'.
]

This equation is a candidate decomposition interface, not a license to fit (U_I), (J), or (epsilon) freely to the same orbital data.

## 5. Holonomy-shell susceptibility

Use

[
r^2Omega=Lambda
u,
qquad

u=ell-rac{	au}{2pi}.
]

Then

[
oxed{
rac{partial r}{partial	au}
=
-rac{Lambda^2
u}
{pi r^3kappa_{m epi}^2}.
}
]

The response diverges at the radial marginal-stability boundary (kappa_{m epi}^2	o0). Shell existence and shell stability are distinct.

GREMLIN may use this as a sensitivity diagnostic only after a declared (	au)-to-carrier binding.

## 6. Precession discriminator

For nearly circular motion,

[
Deltaarpi
=
2pileft(rac{Omega}{kappa_{m epi}}-1ight).
]

Near the Kepler branch,

[
oxed{
Deltaarpi
simeq
-pirac{dln K_{m obs}}{dln r}.
}
]

This gives a cross-observable consistency check between the rotation curve and apsidal precession.

## 7. Cross-repository links

- IDT 02JQ branch:
  https://github.com/AdrianLipa90/Informational-Dynamics-of-Time/blob/candidate/idt-eb-bec-orbital-acoustic-v0.1/formalism/02JQ_radial_condensate_profile_classification.md
- FPDG:
  https://github.com/AdrianLipa90/Fundamental-Physics-Dependency-Graph
- RFC:
  https://github.com/AdrianLipa90/Relational-Field-Closure
- Resonant Chemistry:
  https://github.com/AdrianLipa90/Resonant-Chemistry
- Orbital Eclipse Spectroscopy:
  https://github.com/AdrianLipa90/Orbital-Eclipse-Spectroscopy
- QHTRI phase optics:
  https://github.com/AdrianLipa90/QHTRI-Induced-Holonomic-Potentials-for-Neutrino-Flavour-Transport-and-Phase-Optics

## 8. Authority firewall

PASS within this gate means the algebraic diagnostic is implemented/tested. It does not:
- promote a Bose-Einstein condensate as the physical carrier;
- identify (q_G=m_I);
- identify GREMLIN (	au) with a physical condensate flux;
- calibrate RFC (c_I);
- promote an analogue/phase-optics scalar to spacetime metric curvature.
