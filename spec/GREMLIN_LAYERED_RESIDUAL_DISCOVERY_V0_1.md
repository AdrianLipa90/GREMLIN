# GREMLIN Layered Residual Discovery Gate v0.1

Status: CANDIDATE / SYNTHETIC ADVERSARIAL PASS

A residual may contain multiple superposed mechanisms.

The lawful sequence is not destructive denoising. It is:

RAW
-> MODEL_0
-> RESIDUAL_0
-> identify a supported nuisance relation
-> MODEL_1 = MODEL_0 + admitted nuisance component
-> RESIDUAL_1
-> test residual_1 independently.

Synthetic witness:

- 16 runs x 4096 samples;
- instrument/nuisance sinusoid amplitude 2.0 at bin 31;
- weak persistent structure amplitude 0.10 at bin 137;
- white-noise sigma 1.0.

With MODEL_0=0, the residual is correctly typed SYSTEMATIC_OR_INSTRUMENTAL_CANDIDATE with median nuisance correlation >0.80 and consensus bin 31.

With MODEL_1 equal to the explicitly admitted nuisance term, the unchanged raw observation yields a second residual typed UNRESOLVED_STRUCTURED_CANDIDATE at bin 137. The stacked peak-to-median ratio exceeds 12 and all runs support the bin.

The raw commitment is identical across both stages. Model and residual commitments change, so the provenance records exactly which explanatory layer was introduced.

This does not identify the weak structure physically. It demonstrates that an instrument-dominated residual can contain a second reproducible structure that would be lost by destructive denoising or by labeling the whole first residual as noise.
