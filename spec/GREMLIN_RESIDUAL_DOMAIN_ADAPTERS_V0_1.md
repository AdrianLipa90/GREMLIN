# GREMLIN Residual Domain Adapters v0.1

Status: CANDIDATE / IMPLEMENTED / NO PHYSICAL PROMOTION

This contract sits downstream of GREMLIN Residual-Preserving Spectroscopy v0.2.

Shared residual evidence is kept domain-neutral. A domain adapter may only declare that the relevant confound/control surface is complete enough for a domain-specific holdout. It may not convert residual structure into a physical interpretation.

## Telescope controls

Required before a structured residual can enter telescope holdout:

- LSF or declared spectral response;
- wavelength/pixel jitter;
- gain drift;
- bad-pixel mask;
- detector noise;
- timestamps/clock;
- sampling/alias control;
- known spectral-template control.

## Microscope controls

Required before a structured residual can enter microscope holdout:

- PSF/OTF;
- stage XY drift;
- focus/Z drift;
- illumination gain or bleaching;
- pixel registration;
- detector noise;
- scan-clock jitter;
- sample motion/deformation;
- known structure template.

## Firewall

A complete control surface means only:

READY_FOR_DOMAIN_HOLDOUT_NOT_PHYSICAL_PROMOTION.

It never means astrophysical signal, microscopic physical mechanism, new physics, or time fluctuation established.
