# GREMLIN Residual Red-Team v0.19 — RAW Dependence Before Preprocessing

Status: PREPROCESSING-ORDER NO-GO REPRODUCED / RAW KSG FAMILY AUDIT CANDIDATE / NO CANON PROMOTION

Date: 2026-09-28

## Failure inherited from v0.18

v0.18 correctly showed that a finite handcrafted nonlinear feature bank is not a universal independence test.

A second problem is now pinned: applying detrend/notch before the run-dependence audit can destroy the very nonlinear relation the audit is supposed to detect.

The deterministic witness uses

[
x_0(t)=sqrt2cosphi_t,
qquad
x_1(t)=sqrt2cos(17phi_t)
       =sqrt2,T_{17}(x_0(t)/sqrt2),
]

with the remaining runs independent.

Thus run 1 is an exact deterministic function of run 0.

With 8 runs x 256 samples and a content-addressed 199-world IAAFT null:

- RAW max-pair KSG MI identifies pair (0,1), observed MI about 0.2778, p=0.005;
- after the existing detrend/notch operator, the family maximum moves to another pair and p rises to about 0.39.

A separate 255-world strict prototype gave the same qualitative result:

- RAW p=1/256=0.00390625;
- NOTCHED p=0.421875.

Therefore:

[
oxed{
	ext{postprocessed dependence PASS}

otRightarrow
	ext{RAW run independence}
}
]

and a postprocessing audit cannot rehabilitate a RAW dependence failure.

## v0.19 ordering rule

The dependency firewall is reordered:

1. RAW residual run-dependence audit;
2. only if RAW audit is admissible and does not reject, allow downstream detrend/notch analyses;
3. retain v0.18/v0.12 postprocessing audits as additional diagnostics, not as substitutes for RAW independence.

## Candidate statistic

v0.19 uses a pure-NumPy KSG-1 mutual-information estimator with fixed k=3.

For each RAW run pair, estimate KSG MI and take the maximum over all run pairs.

One joint null world independently IAAFT-surrogates every run while preserving each run's empirical marginal and approximating its power spectrum.

The same complete surrogate bank is then scored with the identical max-pair KSG statistic.

This is a familywise max-null over run pairs.

The Monte-Carlo p-value is

[
p =
rac{1+#{T_{m null}ge T_{m obs}}}
     {B+1}.
]

Null RNG is content-addressed from the RAW residual commitment.

## Fail-closed surfaces

v0.19 abstains before KSG inference when:

- IAAFT applicability is not declared;
- obvious RAW nonstationarity is detected;
- extreme RAW long memory crosses the inherited abstention gate;
- exact sample ties are present;
- IAAFT surrogate spectral fidelity is inadequate;
- the null ensemble cannot resolve the requested alpha.

Exact ties are deliberately not repaired with hidden jitter.

## Independent prototype controls

At alpha 0.005, 255 null worlds, 8 runs x 128 samples, five seeds each:

- white Gaussian: 5/5 no false invalidation;
- Student-t3: 5/5;
- AR(1), phi=0.8: 5/5;
- GARCH-like: 5/5;
- bursty heavy-tail: 5/5.

This 25-trial bank is exploratory calibration, not a formal false-positive bound.

## Finite-sample power warning

The candidate is not universally powerful at finite N.

At 8 runs x 128 samples:

- quadratic deterministic relation: detected;
- Chebyshev m=5: detected;
- Chebyshev m=7: detected;
- Chebyshev m=17: missed in the exploratory seed.

At 8 runs x 256 samples the same m=17 family is detected and the correct pair becomes the family maximum.

Therefore:

[
oxed{
	ext{RAW KSG PASS}

eq
	ext{proof of independence}
}
]

even though mutual information is an appropriate population dependence target.

## Literature anchor

KSG estimator:
Kraskov, Stögbauer, Grassberger,
Estimating Mutual Information,
Physical Review E 69, 066138 (2004),
DOI 10.1103/PhysRevE.69.066138.

Related universal dependence measures remain useful comparison lanes:

- Székely, Rizzo, Bakirov, distance correlation, Annals of Statistics 35 (2007), DOI 10.1214/009053607000000505;
- Gretton et al., kernel independence testing / HSIC.

v0.19 does not claim these population properties automatically provide finite-sample power under the present familywise IAAFT design.

## Claim boundary

RAW dependence rejection invalidates the independent-run cross-fit assumption under this audit.

It does not identify the physical cause.

RAW audit PASS does not prove arbitrary independence.

No result establishes physical mechanism, new physics, or time fluctuations.
