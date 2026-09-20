# GREMLIN Relational Measurement Channel Catalog v0.1

Status: `CANDIDATE_TYPED_CATALOG / SOURCE_SIGNATURE_REQUIRES_DECLARED_MODEL / INDEPENDENCE_FAIL_CLOSED`

This catalog turns the already-derived orbital, condensate, phase-optics, holonomy and spectroscopy observables into typed candidate measurement channels for identifiability-driven experiment design.

It does **not** invent source signatures. A channel receives a source-family sensitivity row only through an explicit response model or chain rule.

## 1. Source-family sensitivity row

For candidate source amplitudes

[
mathbf a=(a_1,ldots,a_p)^T
]

and measured observable (y), define

[
oxed{
mathbf q_y
=
rac{partial y}{partialmathbf a}
}
]

evaluated at the declared local model point.

The measurement-design layer consumes (mathbf q_y), its covariance/variance and provenance.

A channel name alone is never enough to generate (mathbf q_y).

## 2. Channel roles

Every catalog entry has one of four roles.

### SOURCE_SENSITIVE_CONDITIONAL

An exact response operator exists once source-to-field derivatives are supplied.

### NUISANCE_CONTROL

The observable primarily constrains a nuisance/control sector such as density, interaction strength or quantum pressure. It receives a source-family signature only if a separate source-to-control map is explicitly declared.

### MODEL_CONSISTENCY

The observable tests the declared model class but is not automatically an independent source-sensitive row.

### CUSTOM_RESPONSE_REQUIRED

The upstream formalism admits the observable, but no universal source response exists. A model-specific Jacobian must be supplied.

## 3. Independence firewall

A derived observable can be algebraically useful without supplying independent information.

Examples:

[
K'_{m obs}
=
r^2(kappa_{m epi}^2-Omega^2)
]

and

[
rac{partial^2Phi}{partial b^2}
=
rac{b^2}{r^2}kappa_{m epi}^2
+
left(1-rac{4b^2}{r^2}ight)Omega^2
]

can be reconstructed from the same orbital inputs.

Therefore catalog entries carry an `independence_default` flag.

`false` means that GREMLIN must not count the channel as an independent Fisher row unless:
- the user/model declares an independent readout; or
- the joint covariance with existing measurements is supplied and the Schur-complement update is used.

## 4. Radial-scalar response operators

Let source family (j) contribute local scalar derivatives

[
f_j(r)=partial_rPhi_j,
qquad
h_j(r)=partial_r^2Phi_j.
]

Then

[
oxed{
q_{Omega^2,j}
=
rac{f_j}{r}
}
]

and

[
oxed{
q_{kappa^2,j}
=
h_j+rac{3f_j}{r}.
}
]

Therefore

[
oxed{
q_{K'_{m obs},j}
=
r^2
left(
q_{kappa^2,j}-q_{Omega^2,j}
ight).
}
]

For impact parameter (b),

[
oxed{
q_{partial_bPhi,j}
=
b,q_{Omega^2,j},
}
]

and

[
oxed{
q_{partial_b^2Phi,j}
=
rac{b^2}{r^2}q_{kappa^2,j}
+
left(1-rac{4b^2}{r^2}ight)q_{Omega^2,j}.
}
]

The radial/tangential Hessian rows are

[
oxed{
q_{lambda_r,j}
=
q_{kappa^2,j}-3q_{Omega^2,j}
=
h_j,
}
]

[
oxed{
q_{lambda_t,j}
=
q_{Omega^2,j}.
}
]

These are exact within the declared stationary central scalar model.

## 5. Holonomy-shell response

For the conditional shell susceptibility

[
rac{partial r}{partial	au}
=
-rac{Lambda^2
u}
{pi r^3kappa_{m epi}^2},
]

and a declared source-to-holonomy Jacobian

[
mathbf t
=
rac{partial	au}{partialmathbf a},
]

the shell-radius source row is

[
oxed{
mathbf q_r
=
rac{partial r}{partial	au},
mathbf t.
}
]

This requires the same-loop holonomy binding and remains conditional.

## 6. Spectral chain rule

For any spectroscopic observable (mathcal O) with loop-phase Jacobian

[
mathbf j_{mathcal O}
=
rac{partialmathcal O}{partialoldsymbolPhi}
]

and source-to-loop-phase map

[
T_Phi
=
rac{partialoldsymbolPhi}{partialmathbf a},
]

the source-family signature is

[
oxed{
mathbf q_{mathcal O}
=
mathbf j_{mathcal O}T_Phi.
}
]

For a line frequency,

[
rac{partialomega_{mn}}{partialPhi_a}
=
-rac{J_{m,a}-J_{n,a}}{hbar},
]

therefore

[
oxed{
mathbf q_{omega_{mn}}
=
-rac{mathbf J_m-mathbf J_n}{hbar}
T_Phi.
}
]

The same chain-rule interface can be used for:
- intensity;
- linewidth;
- coherent beat frequency;
- 2D cross-peak amplitude;
- phase-resolved observables;

but only when their upstream phase Jacobian is explicitly supplied.

## 7. Thomas–Fermi / Bogoliubov control channels

Under the conditional 02JP Thomas–Fermi branch,

[
c_s^2
=
rac{
mu_c-U_{m ext}-U_I
}{m_B}.
]

If the source-family derivative maps are explicitly declared,

[
mathbf q_{mu_c},
quad
mathbf q_{U_{m ext}},
quad
mathbf q_{U_I},
]

then

[
oxed{
mathbf q_{c_s^2}
=
rac{
mathbf q_{mu_c}
-
mathbf q_{U_{m ext}}
-
mathbf q_{U_I}
}{m_B}.
}
]

For fixed (m_B) and the conservative Bogoliubov dispersion

[
omega_{m Bog}^2
=
c_s^2 k^2
+
rac{hbar^2 k^4}{4m_B^2},
]

the source row is

[
oxed{
mathbf q_{omega_{m Bog}^2}
=
k^2mathbf q_{c_s^2}.
}
]

Density imaging and quantum-pressure reconstruction are catalogued as nuisance/control channels by default. They are not assigned source signatures unless a source-to-density model is declared.

## 8. Canonical catalog v0.1

The catalog contains the following channel IDs.

### Orbital / radial

- `ORBITAL_OMEGA_SQ`
- `EPICYCLIC_KAPPA_SQ`
- `KOBS_GRADIENT`
- `CENTRAL_CONSISTENCY_RESIDUAL`
- `CONDENSATE_SUBTRACTED_RADIAL_RESIDUAL`

### Condensate / control

- `DENSITY_GRADIENT`
- `QUANTUM_PRESSURE_GRADIENT`
- `BOGOLIUBOV_SOUND_SPEED_SQ`
- `BOGOLIUBOV_DISPERSION_OMEGA_SQ`

### Holonomy

- `HOLONOMY_LOOP_PHASE`
- `HOLONOMY_SHELL_RADIUS`

### Phase optics

- `TRANSVERSE_PHASE_GRADIENT`
- `TRANSVERSE_PHASE_CURVATURE`
- `RADIAL_HESSIAN_EIGENVALUE`
- `TANGENTIAL_HESSIAN_EIGENVALUE`

### Spectroscopy

- `SPECTRAL_LINE_FREQUENCY`
- `SPECTRAL_INTENSITY`
- `SPECTRAL_LINEWIDTH`
- `SPECTRAL_COHERENT_BEAT`
- `SPECTRAL_2D_CROSS_PEAK`
- `SPECTRAL_PHASE_RESOLVED`

## 9. Model-consistency versus information

`CENTRAL_CONSISTENCY_RESIDUAL` is primarily a falsification channel:

[
mathcal B
=
kappa_{m meas}^2
-
4Omega_{m meas}^2
-
r,rac{dOmega_{m meas}^2}{dr}.
]

A nonzero value rejects at least one declared central-model assumption. It must not be attributed automatically to a candidate source family.

Likewise a channel derived deterministically from another readout must not be double counted.

## 10. Provenance

Every instantiated channel must carry:
- catalog channel ID;
- exact upstream repository/path/commit;
- local response-model identifier;
- source-family names/order;
- exact sensitivity row;
- uncertainty/covariance binding;
- independence declaration;
- epistemic status.

## 11. Cross-repository parents

IDT 02JP/02JQ:
https://github.com/AdrianLipa90/Informational-Dynamics-of-Time/pull/101

OES H1:
https://github.com/AdrianLipa90/Orbital-Eclipse-Spectroscopy/pull/14

QHTRI phase optics:
https://github.com/AdrianLipa90/QHTRI-Induced-Holonomic-Potentials-for-Neutrino-Flavour-Transport-and-Phase-Optics/pull/1

Resonant Chemistry holonomy spectroscopy:
https://github.com/AdrianLipa90/Resonant-Chemistry/pull/27

GREMLIN measurement design:
https://github.com/AdrianLipa90/GREMLIN/pull/88

MAS:
https://github.com/AdrianLipa90/PhaseNav-MAS-Upgrade

## 12. Status firewall

The catalog formalizes observable interfaces already present in the linked candidate branches.

It does not establish:
- physical (W_{m chem}=W_{m sem});
- physical BEC realization;
- RFC information coupling calibration;
- spacetime metric binding;
- independence of two observables merely because they have different names;
- a universal source signature without a declared source-response model.
