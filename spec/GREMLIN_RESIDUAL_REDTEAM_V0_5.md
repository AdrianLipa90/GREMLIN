# GREMLIN Residual Red-Team v0.5

Status: CANDIDATE / RED-TEAM HARDENING / NO CANON PROMOTION

Date: 2026-09-28

## Why v0.5 exists

v0.4 fixed four concrete pre-fix failures:

1. AR(1) colored noise promoted by the old global peak/median rule;
2. alternating-sign offsets mislabeled as persistent offsets;
3. half-bin spectral leakage hiding a weak line;
4. pure-noise nuisance accepted after searching a 64-candidate family.

Further adversarial work found two additional structural weaknesses and one provenance boundary.

## A. First-difference blindness is frequency dependent

The v0.4 narrowband gate requires persistence in both the raw residual and its first difference.

For a discrete Fourier mode k in a record of length N, the first-difference transfer gain is

[
g_Delta(k)=2left|sinrac{pi k}{N}ight|.
]

Therefore low-cycle structure is attenuated by construction.

Independent Monte Carlo reimplementation at N=4096, 16 runs, white-noise sigma 1 and line amplitude 0.2 showed:

- bin 2: 0/20 through the v0.4 narrowband gate;
- bin 3: 0/20;
- bin 5: 0/20;
- bin 10: 18/20;
- bin 30 and above: 20/20.

The failure is not random. It follows from the transfer function.

v0.5 therefore does not force a feature through first-difference validation when the transfer gain itself is below a declared floor.

Such a feature is not called a line. It is typed:

[
	exttt{UNRESOLVED_DIFFERENCE_ATTENUATED_SPECTRAL_FEATURE_CANDIDATE}.
]

A smooth log-power spectral continuum is fitted on held-out runs and the candidate band must show an excess over that continuum.

The supplemental gate preserves low-cycle structure while keeping the original v0.4 narrowband route unchanged at frequencies where differencing is informative.

## B. Spectral morphology is not ontology

Adversarial backgrounds included:

- white noise;
- AR(1) with several phi values;
- 1/f^alpha with alpha from 0.5 to 2.5;
- random walk;
- broken power-law knees;
- finite-width spectral bumps.

Simple stationary white/AR/power-law/random-walk backgrounds produced zero structured detections in the tested Monte Carlo batches.

Broken power-law knees and finite-width bumps can produce real repeatable spectral excesses.

That is not a false observation of structure. The error would be to call all such excesses a single physical line.

v0.5 therefore preserves the feature while refusing line/mechanism assignment from morphology alone.

## C. Recursive alpha must be global, not renewed each round

A deterministic stress at loose settings produced a concrete reproducer:

seed 10029
8 runs x 64 samples
1 true nuisance + 7 independent noise proxies.

With a per-round familywise alpha of 0.05 and only 31 null worlds:

[
[	exttt{true},	exttt{noise02}]
]

was selected.

The second-layer noise proxy had conservative holdout gain about 0.0172.

Increasing null worlds alone did not close the reproducer while keeping a per-round alpha of 0.01.

The reproducer closed when the total alpha budget 0.01 was allocated across at most 8 rounds:

[
alpha_{m round}=0.01/8=0.00125.
]

v0.5 therefore introduces a global alpha ledger.

## D. Shared synchronized null worlds

Familywise max-null requires a joint null world.

v0.4 constructed each candidate's null sequence independently, then combined same-index entries into a family maximum.

v0.5 instead creates one deterministic shared null world per index:

- measured instrument/environment/clock channels share the same run permutation;
- phase/spectral templates share the same per-run circular-shift vector.

This preserves candidate-family dependence under the null transformation more faithfully.

The familywise adjusted empirical p-value is

[
p_{m adj}
=
rac{1+#{M_bge T_{m obs}}}{B+1},
]

where (M_b) is the maximum nuisance score in shared null world b.

A candidate must satisfy

[
p_{m adj}lealpha_{m round}.
]

## E. Null-resolution fail-closed gate

The empirical permutation resolution is finite.

For round alpha (alpha_r), v0.5 requires

[
Bgeleftlceilrac1{alpha_r}ightceil-1.
]

At total alpha 0.01 and max_layers=8 this requires at least 799 null worlds.

The default is 1023.

For run-permutation nulls, the requested count must also not exceed the number of unique nonidentity run permutations.

The code fails closed when either resolution condition is impossible.

## F. Power cost

The hardening is not free.

An independent shared-null semantic Monte Carlo with one true nuisance plus seven noise candidates gave:

- amplitude 0.5 sigma: 10/10 true first, 0 false layers in the first checkpointed batches;
- amplitude 0.3 sigma: 5/5 true first, 0 false layers;
- amplitude 0.2 sigma: 1/5 true recovered, 0 false layers.

Therefore v0.5 is substantially more conservative near the detection boundary.

This is a real power/specificity trade-off and remains an empirical calibration gate.

## G. Provenance boundary: a boolean is not evidence

The existing metadata field

[
	exttt{independent_of_target_fit=True}
]

is only a declaration.

A target-derived channel mislabeled as independent can still be statistically predictive.

GREMLIN already contains a strong acquisition-bound validator for live NOEMA/CIEL lineage, but that validator is intentionally tied to the canonical live NOEMA surface.

It must not be repurposed to pretend that telescope/JWST telemetry has NOEMA provenance.

Therefore v0.5 statistical acceptance means:

[
oxed{	ext{predictively admitted nuisance candidate}}
]

not:

[
oxed{	ext{independently acquired physical nuisance}}
]

unless an appropriate upstream acquisition receipt has itself been validated.

A generic external instrument acquisition receipt remains an open prerequisite for telescope-grade causal/provenance promotion.

## H. Current evidence status

Independent semantic replay, not exact branch pytest, produced:

- 0/400 structured false positives across white / AR(1) / 1/f / random-walk baseline batches;
- recovery of 0.2-sigma low-cycle lines through the supplemental feature route;
- preservation of higher-frequency line detections through the original v0.4 narrowband path;
- seed 10029 closed by global alpha accounting in the shared-null reimplementation.

The exact private-branch pytest replay could not be executed in the current container because the container has no GitHub DNS access, and the alternate remote Python runtime rejected execution for missing team authorization.

Therefore exact-branch execution remains OPEN.

## Claim boundary

v0.5 does not establish:

- globally exact sequential FWER under all adaptive-selection conditions;
- causal identity of an admitted nuisance;
- a physical interpretation of any residual spectral feature;
- astrophysical origin;
- new physics;
- time fluctuations.

It hardens candidate generation and makes the remaining open gates explicit.
